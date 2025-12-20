import azure.functions as func
import json
import logging
import os
from azure.cosmos import CosmosClient

app = func.FunctionApp()

@app.route(route="sensor-data", methods=["POST"])
def sensor_data_handler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Sensor data received')
    
    try:
        req_body = req.get_json()
        
        if not req_body or 'deviceId' not in req_body or 'sensors' not in req_body:
            return func.HttpResponse(
                "Missing required fields: deviceId, sensors",
                status_code=400
            )
        
        # Store in Cosmos DB
        client = CosmosClient(os.environ['COSMOS_ENDPOINT'], os.environ['COSMOS_KEY'])
        database = client.get_database_client(os.environ['COSMOS_DATABASE'])
        container = database.get_container_client(os.environ['COSMOS_CONTAINER'])
        
        container.create_item(body=req_body)
        
        return func.HttpResponse(
            json.dumps({"status": "success", "message": "Data stored"}),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}),
            status_code=500,
            mimetype="application/json"
        )