from flask import Flask, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
from domain import model
from adapters import orm, repository
from service_layer import services

orm.start_mappers()
Session = sessionmaker(bind=create_engine(config.get_postgres_uri()))
app = Flask(__name__)


@app.route("/add_batch", methods=["POST"])
def add_batch_endpoint():
    session = Session()
    repo = repository.SqlAlchemyRepository(session)
    batch = model.Batch(
        reference=request.json["reference"],
        sku=request.json["sku"],
        qty=request.json["qty"],
        eta=request.json.get("eta"),
    )
    services.add_batch(batch, repo, session)

    return {"message": "Created"}, 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    session = Session()
    repo = repository.SqlAlchemyRepository(session)
    line = model.OrderLine(
        request.json["orderid"], request.json["sku"], request.json["qty"]
    )

    try:
        batchref = services.allocate(line, repo, session)
    except (model.OutOfStock, services.InvalidSku) as e:
        return {"message": str(e)}, 400

    return jsonify({"batchref": batchref}), 201


@app.route("/deallocate", methods=["POST"])
def deallocate_endpoint():
    session = Session()
    repo = repository.SqlAlchemyRepository(session)
    line = model.OrderLine(
        request.json["orderid"], request.json["sku"], request.json["qty"]
    )

    services.deallocate(line, repo, session)

    return {"message": "Deallocated"}, 200