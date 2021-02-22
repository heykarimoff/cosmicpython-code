# import flask

# from model import Batch, OrderLine, allocate
# from orm import start_mappers

# from repository import SqlAlchemyRepository


# @flask.route.gubbins
# def allocate_endpoint():
#     session = start_mappers()
#     batches = SqlAlchemyRepository(session).list()

#     lines = [
#         OrderLine(l["orderid"], l["sku"], l["qty"]) for l in request.params
#     ]

#     allocate(lines, batches)

#     session.commit()
#     return 201
