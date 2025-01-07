from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os
import logging
from bson import json_util

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Conexão com MongoDB usando variável de ambiente do Heroku
MONGODB_URI = "mongodb+srv://murilo:daf123@murilo-cluster.pq2xl.mongodb.net/?retryWrites=true&w=majority&appName=murilo-cluster"

try:
    client = MongoClient(MONGODB_URI)
    # Teste de conexão
    client.server_info()
    logger.info("Conexão com MongoDB estabelecida com sucesso!")
    db = client["audit_db"]
    audits_collection = db["audits"]
except Exception as e:
    logger.error(f"Erro ao conectar com MongoDB: {str(e)}")
    raise

@app.route('/')
def home():
    return "API está funcionando!"

@app.route('/submit-audit', methods=['POST'])
def submit_audit():
    try:
        data = request.json
        audits_collection.insert_one(data)
        return jsonify({"message": "Auditoria registrada com sucesso!"}), 201
    except Exception as e:
        logger.error(f"Erro ao submeter auditoria: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@app.route('/audits', methods=['GET'])
def get_audits():
    try:
        audits = list(audits_collection.find({}, {"_id": 0}))
        return jsonify(audits)
    except Exception as e:
        logger.error(f"Erro ao buscar auditorias: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@app.route('/export', methods=['GET'])
def exportar_dados():
    try:
        items = audits_collection.find()
        # Converte ObjectId para string
        result = [{**item, "_id": str(item["_id"])} for item in items]
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Erro ao exportar dados: {str(e)}")
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
