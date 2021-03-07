from datetime import datetime

from adapters import orm, repository
from domain import model
from flask import Flask, jsonify, request
from service_layer import services, unit_of_work

orm.start_mappers()
app = Flask(__name__)


@app.route("/add_batch", methods=["POST"])
def add_batch_endpoint():
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    eta = request.json.get("eta")

    if eta is not None:
        eta = datetime.fromisoformat(eta).date()

    services.add_batch(
        request.json["reference"],
        request.json["sku"],
        request.json["qty"],
        eta=eta,
        uow=uow,
    )

    return "OK", 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    uow = unit_of_work.SqlAlchemyUnitOfWork()

    try:
        batchref = services.allocate(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"],
            uow,
        )
    except (model.OutOfStock, services.InvalidSku) as e:
        return {"message": str(e)}, 400

    return jsonify({"batchref": batchref}), 201


@app.route("/deallocate", methods=["POST"])
def deallocate_endpoint():
    uow = unit_of_work.SqlAlchemyUnitOfWork()

    services.deallocate(
        request.json["orderid"], request.json["sku"], request.json["qty"], uow
    )

    return "OK", 200
