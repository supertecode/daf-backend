from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os
from bson import json_util

app = Flask(__name__)
CORS(app)

# Conexão com MongoDB usando variável de ambiente do Heroku
MONGODB_URI = "mongodb+srv://murilo:daf123@murilo-cluster.pq2xl.mongodb.net/?retryWrites=true&w=majority&appName=murilo-cluster"
client = MongoClient(MONGODB_URI)
db = client["audit_db"]
audits_collection = db["audits"]

@app.route('/submit-audit', methods=['POST'])
def submit_audit():
    data = request.json
    audits_collection.insert_one(data)
    return jsonify({"message": "Auditoria registrada com sucesso!"}), 201

@app.route('/audits', methods=['GET'])
def get_audits():
    audits = list(audits_collection.find({}, {"_id": 0}))
    return jsonify(audits)

@app.route('/export', methods=['GET'])
def exportar_dados():
    try:
        items = audits_collection.find()
        result = [json_util.loads(json_util.dumps(item)) for item in items]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    # Heroku fornece a porta como uma variável de ambiente
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
