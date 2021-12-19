from datetime import datetime

from allocation.adapters import orm
from allocation.domain import events
from allocation.service_layer import handlers, unit_of_work, messagebus
from flask import Flask, jsonify, request

orm.start_mappers()
app = Flask(__name__)


@app.route("/add_batch", methods=["POST"])
def add_batch_endpoint():
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    eta = request.json.get("eta")

    if eta is not None:
        eta = datetime.fromisoformat(eta).date()

    event = events.BatchCreated(
        request.json["reference"],
        request.json["sku"],
        request.json["qty"],
        eta=eta,
    )

    messagebus.handle(event, uow)

    return "OK", 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    uow = unit_of_work.SqlAlchemyUnitOfWork()

    try:
        event = events.AllocationRequired(
            request.json["orderid"], request.json["sku"], request.json["qty"]
        )
        results = messagebus.handle(event, uow)
        batchref = results.pop(0)
    except handlers.InvalidSku as e:
        return {"message": str(e)}, 400

    if not batchref:
        return {"message": "Out of stock"}, 400

    return jsonify({"batchref": batchref}), 201


@app.route("/deallocate", methods=["POST"])
def deallocate_endpoint():
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    try:
        event = events.DeallocationRequired(
            request.json["orderid"], request.json["sku"], request.json["qty"]
        )
        results = messagebus.handle(event, uow)
    except handlers.InvalidSku as e:
        return {"message": str(e)}, 400

    return "OK", 200
