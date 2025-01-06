from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# Conexão com MongoDB
client = MongoClient("mongodb://localhost:27017/")
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

# Endpoint para exportar dados para o Power BI
@app.route('/audits', methods=['GET'])
def exportar_dados():
    try:
        # Obtém todos os documentos da coleção
        items = collection.find()
        # Converte os documentos para um formato JSON serializável
        result = [json_util.loads(json_util.dumps(item)) for item in items]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    #app.run(host='0.0.0.0', port=5000) #Link Local
    app.run(host='localhost', port=5000, debug=True) #Link Online
