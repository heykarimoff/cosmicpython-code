from datetime import datetime

from allocation.adapters import orm
from allocation.domain import commands, events
from allocation.service_layer import handlers, messagebus, unit_of_work
from flask import Flask, jsonify, request

orm.start_mappers()
app = Flask(__name__)


@app.route("/add_batch", methods=["POST"])
def add_batch_endpoint():
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    eta = request.json.get("eta")

    if eta is not None:
        eta = datetime.fromisoformat(eta).date()

    message = commands.CreateBatch(
        request.json["reference"],
        request.json["sku"],
        request.json["qty"],
        eta=eta,
    )

    messagebus.handle(message, uow)

    return "OK", 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    uow = unit_of_work.SqlAlchemyUnitOfWork()

    try:
        message = commands.Allocate(
            request.json["orderid"], request.json["sku"], request.json["qty"]
        )
        results = messagebus.handle(message, uow)
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
        message = commands.Deallocate(
            request.json["orderid"], request.json["sku"], request.json["qty"]
        )
        results = messagebus.handle(message, uow)
    except handlers.InvalidSku as e:
        return {"message": str(e)}, 400

    return "OK", 200
