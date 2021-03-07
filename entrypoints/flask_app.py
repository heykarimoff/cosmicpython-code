from datetime import datetime

import config
from adapters import orm, repository
from domain import model
from flask import Flask, jsonify, request
from service_layer import services
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

orm.start_mappers()
Session = sessionmaker(bind=create_engine(config.get_postgres_uri()))
app = Flask(__name__)


@app.route("/add_batch", methods=["POST"])
def add_batch_endpoint():
    session = Session()
    repo = repository.SqlAlchemyRepository(session)
    eta = request.json.get("eta")

    if eta is not None:
        eta = datetime.fromisoformat(eta).date()

    services.add_batch(
        request.json["reference"],
        request.json["sku"],
        request.json["qty"],
        eta=eta,
        repo=repo,
        session=session,
    )

    return "OK", 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    session = Session()
    repo = repository.SqlAlchemyRepository(session)

    try:
        batchref = services.allocate(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"],
            repo,
            session,
        )
    except (model.OutOfStock, services.InvalidSku) as e:
        return {"message": str(e)}, 400

    return jsonify({"batchref": batchref}), 201


@app.route("/deallocate", methods=["POST"])
def deallocate_endpoint():
    session = Session()
    repo = repository.SqlAlchemyRepository(session)

    services.deallocate(
        request.json["orderid"],
        request.json["sku"],
        request.json["qty"],
        repo,
        session,
    )

    return "OK", 200
