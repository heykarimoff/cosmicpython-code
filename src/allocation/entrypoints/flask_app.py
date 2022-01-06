from datetime import datetime

from allocation import bootstrap, views
from allocation.domain import commands
from allocation.service_layer import handlers, unit_of_work
from flask import Flask, jsonify, request

app = Flask(__name__)
messagebus = bootstrap.bootstrap()


@app.route("/add_batch", methods=["POST"])
def add_batch_endpoint():
    eta = request.json.get("eta")

    if eta is not None:
        eta = datetime.fromisoformat(eta).date()

    message = commands.CreateBatch(
        request.json["reference"],
        request.json["sku"],
        request.json["qty"],
        eta=eta,
    )

    messagebus.handle(message)

    return {"message": "OK"}, 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        message = commands.Allocate(
            request.json["orderid"], request.json["sku"], request.json["qty"]
        )
        results = messagebus.handle(message)
        batchref = results.pop(0)
    except handlers.InvalidSku as e:
        return {"message": str(e)}, 400

    if not batchref:
        return {"message": "Out of stock"}, 400

    return {"message": "OK"}, 202


@app.route("/deallocate", methods=["POST"])
def deallocate_endpoint():
    try:
        message = commands.Deallocate(
            request.json["orderid"], request.json["sku"], request.json["qty"]
        )
        messagebus.handle(message)
    except handlers.InvalidSku as e:
        return {"message": str(e)}, 400

    return {"message": "OK"}, 200


@app.route("/allocations/<orderid>", methods=["GET"])
def allocations_view_endpoint(orderid):
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    result = views.allocations(orderid, uow)
    if not result:
        return {"message": "Not found"}, 404
    return jsonify(result), 200
