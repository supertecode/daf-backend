from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from functools import wraps
from datetime import datetime, timedelta
import os
import logging
from bson import json_util, ObjectId

DATE_FORMAT = "%d/%m/%Y"

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Substitua por uma chave secreta segura

# Conexão com MongoDB usando variável de ambiente
MONGODB_URI = "mongodb+srv://murilo:daf123@murilo-cluster.pq2xl.mongodb.net/?retryWrites=true&w=majority&appName=murilo-cluster"

try:
    client = MongoClient(MONGODB_URI)
    # Teste de conexão
    client.server_info()
    logger.info("Conexão com MongoDB estabelecida com sucesso!")
    db = client["audit_db"]
    audits_collection = db["audits"]
    users_collection = db["users"]
except Exception as e:
    logger.error(f"Erro ao conectar com MongoDB: {str(e)}")
    raise

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token ausente!'}), 401
        
        try:
            token = token.split(" ")[1]  # Remove "Bearer " do token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = users_collection.find_one({'username': data['username']})
        except Exception as e:
            logger.error(f"Erro na validação do token: {str(e)}")
            return jsonify({'message': 'Token inválido!'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/')
def home():
    return "API está funcionando!"

@app.route('/register', methods=['POST'])
@token_required
def register_user(current_user):
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Sem permissão!'}), 403
    
    data = request.json
    
    if users_collection.find_one({'username': data['username']}):
        return jsonify({'message': 'Usuário já existe!'}), 400
    
    new_user = {
        'username': data['username'],
        'password': generate_password_hash(data['password']),
        'role': data['role'],  # 'auditor' ou 'admin'
        'name': data['name']
    }
    
    users_collection.insert_one(new_user)
    return jsonify({'message': 'Usuário registrado com sucesso!'}), 201

@app.route('/login', methods=['POST'])
def login():
    try:
        auth = request.json
        logger.info(f"Tentativa de login para usuário: {auth['username']}")
        
        user = users_collection.find_one({'username': auth['username']})
        
        if not user:
            logger.warning(f"Usuário não encontrado: {auth['username']}")
            return jsonify({'message': 'Credenciais inválidas!'}), 401

        # Log do hash armazenado para debug
        logger.info(f"Hash tipo armazenado: {user['password'][:50]}...")
        
        if not check_password_hash(user['password'], auth['password']):
            logger.warning(f"Senha incorreta para usuário: {auth['username']}")
            return jsonify({'message': 'Credenciais inválidas!'}), 401
        
        token = jwt.encode({
            'username': user['username'],
            'role': user['role'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'])
        
        return jsonify({
            'token': token,
            'user': {
                'username': user['username'],
                'role': user['role'],
                'name': user['name']
            }
        })
    except Exception as e:
        logger.error(f"Erro no login: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@app.route('/submit-audit', methods=['POST'])
@token_required
def submit_audit(current_user):
    try:
        if current_user['role'] != 'auditor':
            return jsonify({'message': 'Sem permissão!'}), 403
        
        data = request.json
        
        # Verifica se já existe uma auditoria do mesmo auditor para o mesmo setor na mesma data
        today = datetime.now().strftime(DATE_FORMAT)
        existing_audit = audits_collection.find_one({
            'auditor': current_user['name'],
            'setor': data['setor'],
            'data': today
        })
        
        if existing_audit:
            return jsonify({
                'message': 'Já existe uma auditoria para este setor hoje!',
                'auditId': str(existing_audit['_id'])
            }), 409
        
        data['auditor'] = current_user['name']
        data['data'] = today
        result = audits_collection.insert_one(data)
        
        return jsonify({
            "message": "Auditoria registrada com sucesso!",
            "auditId": str(result.inserted_id)
        }), 201
    except Exception as e:
        logger.error(f"Erro ao submeter auditoria: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@app.route('/audits', methods=['GET'])
@token_required
def get_audits(current_user):
    try:
        # Se for auditor, retorna apenas suas próprias auditorias
        if current_user['role'] == 'auditor':
            audits = list(audits_collection.find(
                {'auditor': current_user['name']},
                {"_id": 1, "setor": 1, "data": 1, "notas": 1, "observacoes": 1}
            ))
        else:
            audits = list(audits_collection.find({}, {"_id": 1, "setor": 1, "data": 1, "notas": 1, "observacoes": 1, "auditor": 1}))
        
        # Converter ObjectId para string
        for audit in audits:
            audit['_id'] = str(audit['_id'])
            
        return jsonify(audits)
    except Exception as e:
        logger.error(f"Erro ao buscar auditorias: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@app.route('/export', methods=['GET'])
def exportar_dados():
    try:
        # Obtém todos os documentos da coleção
        items = audits_collection.find()
        # Converte os documentos para um formato JSON serializável
        result = [json_util.loads(json_util.dumps(item)) for item in items]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/users', methods=['GET'])
@token_required
def get_users(current_user):
    try:
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Sem permissão!'}), 403
        
        # Busca todos os usuários, excluindo o hash da senha da resposta
        users = list(users_collection.find({}, {'password': 0}))
        # Converte ObjectId para string para poder serializar
        for user in users:
            user['_id'] = str(user['_id'])
        
        return jsonify(users)
    except Exception as e:
        logger.error(f"Erro ao buscar usuários: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@app.route('/audits/<audit_id>', methods=['DELETE'])
@token_required
def delete_audit(current_user, audit_id):
    try:
        # Busca a auditoria
        audit = audits_collection.find_one({'_id': ObjectId(audit_id)})
        
        if not audit:
            return jsonify({'message': 'Auditoria não encontrada!'}), 404
            
        # Verifica se o auditor é dono da auditoria
        if current_user['role'] != 'admin' and audit['auditor'] != current_user['name']:
            return jsonify({'message': 'Sem permissão para deletar esta auditoria!'}), 403
            
        # Verifica se a auditoria é do mesmo dia
        if audit['data'] != datetime.now().strftime(DATE_FORMAT):
            return jsonify({'message': 'Só é possível deletar auditorias do dia atual!'}), 403
        
        result = audits_collection.delete_one({'_id': ObjectId(audit_id)})
        
        if result.deleted_count > 0:
            return jsonify({'message': 'Auditoria deletada com sucesso!'}), 200
        else:
            return jsonify({'message': 'Auditoria não encontrada!'}), 404
    except Exception as e:
        logger.error(f"Erro ao deletar auditoria: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@app.route('/audits/<audit_id>', methods=['PUT'])
@token_required
def update_audit(current_user, audit_id):
    try:
        # Busca a auditoria
        audit = audits_collection.find_one({'_id': ObjectId(audit_id)})
        
        if not audit:
            return jsonify({'message': 'Auditoria não encontrada!'}), 404
            
        # Verifica se o auditor é dono da auditoria
        if current_user['role'] != 'admin' and audit['auditor'] != current_user['name']:
            return jsonify({'message': 'Sem permissão para atualizar esta auditoria!'}), 403
            
        # Verifica se a auditoria é do mesmo dia
        if audit['data'] != datetime.now().strftime(DATE_FORMAT):
            return jsonify({'message': 'Só é possível atualizar auditorias do dia atual!'}), 403
        
        data = request.json
        data['auditor'] = audit['auditor']  # Mantém o auditor original
        data['data'] = audit['data']  # Mantém a data original
        
        audits_collection.update_one(
            {'_id': ObjectId(audit_id)},
            {'$set': data}
        )
        
        return jsonify({'message': 'Auditoria atualizada com sucesso!'}), 200
    except Exception as e:
        logger.error(f"Erro ao atualizar auditoria: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@app.route('/users/<user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Sem permissão!'}), 403

    from bson.objectid import ObjectId
    
    # Verifica se é o último administrador
    admin_count = users_collection.count_documents({'role': 'admin'})
    user_to_delete = users_collection.find_one({'_id': ObjectId(user_id)})
    
    if user_to_delete['role'] == 'admin' and admin_count <= 1:
        return jsonify({'message': 'Não é possível deletar o último administrador!'}), 400
    
    # Deleta o usuário
    result = users_collection.delete_one({'_id': ObjectId(user_id)})
    
    if result.deleted_count > 0:
        return jsonify({'message': 'Usuário deletado com sucesso!'}), 200
    else:
        return jsonify({'message': 'Usuário não encontrado!'}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
