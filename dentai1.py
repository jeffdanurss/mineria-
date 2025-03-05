from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import cv2
import numpy as np
from ultralytics import YOLO  # Importar YOLO desde ultralytics
from werkzeug.utils import secure_filename
from datetime import datetime
from pathlib import PosixPath, WindowsPath
import pathlib
import markdown
import google.generativeai as genai  # Para Gemini
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

# Configuración inicial
pathlib.PosixPath = pathlib.WindowsPath

# Configurar Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError(
        "No se encontró la clave API de Gemini. Asegúrate de configurar la variable de entorno GEMINI_API_KEY.")
genai.configure(api_key=API_KEY)

# Inicializar la aplicación Flask y SocketIO
app = Flask(__name__)
socketio = SocketIO(app)

# Configurar directorios fijos
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
RESULTS_FOLDER = os.path.join(BASE_DIR, 'static', 'results')
ORIGINAL_IMAGE = os.path.join(UPLOAD_FOLDER, 'original.jpg')
YOLO_RESULT_IMAGE = os.path.join(RESULTS_FOLDER, 'yolo_result.jpg')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Umbral de confianza para las predicciones
THRESHOLD = 0.001  # Ajustar este valor según las necesidades
# Funcion para cargar el modelo YOLO único
def load_yolo_model():
    print("Cargando modelo YOLO 'best.pt'...")
    return YOLO('modelos/best.pt')# Solo se usa best.pt

# Función para procesar con el modelo YOLO seleccionado
def process_yolo_with_selected_model(image_path, model):
    original_img = cv2.imread(image_path)
    detected_diseases = []  # Inicializar como una lista vacía
    results = model(image_path)  # Obtener los resultados del modelo YOLO

    # Iterar sobre los resultados del modelo
    for result in results:
        boxes = result.boxes.xyxy.cpu().numpy()  # Obtener las cajas delimitadoras
        confidences = result.boxes.conf.cpu().numpy()  # Obtener las confianzas
        class_ids = result.boxes.cls.cpu().numpy()  # Obtener los IDs de las clases

        for box, conf, cls_id in zip(boxes, confidences, class_ids):
            if conf >= THRESHOLD:  # Filtrar por el umbral de confianza
                x1, y1, x2, y2 = map(int, box)
                label = model.names[int(cls_id)]  # Obtener el nombre de la clase
                confidence = float(conf)
                color = (0, 255, 0)
                cv2.rectangle(original_img, (x1, y1), (x2, y2), color, 2)
                label_text = f'{label} {confidence:.2f}'
                cv2.putText(original_img, label_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                detected_diseases.append((label, confidence))  # Agregar enfermedad detectada

    # Guardar la imagen con las detecciones
    cv2.imwrite(YOLO_RESULT_IMAGE, original_img)

    # Si no se detectaron enfermedades, devolver un mensaje de error
    if not detected_diseases:
        return {"error": "La imagen no contiene dientes o no es válida. Intenta con otra imagen."}

    return detected_diseases

# Función para generar embeddings con Gemini

def generate_embedding(text):
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",  # Modelo de embeddings
            content=text
        )
        return result['embedding']
    except Exception as e:
        print(f"Error al generar el embedding: {e}")
        return None

# Diccionario de enfermedades y sus descripciones
diseases = {
    "calculo": "Sarro acumulado sobre la superficie dental.",
    "cancer": "Crecimiento anormal de células en la cavidad oral.",
    "caries": "Areas dañadas en la superficie de los dientes que se desarrollan en pequeños orificios o cavidades.",
    "gingivitis": "Inflamación de las encías ",
    "perdidos": "Dientes perdidos o ausentes",
    "placa": "Película pegajosa y blanda que se forma continuamente sobre la superficie de los dientes.",
    "ulceras": "Lesiones abiertas en la mucosa oral que pueden ser dolorosas."
}

# Generar y almacenar embeddings
disease_embeddings = {disease: generate_embedding(description) for disease, description in diseases.items()}

# Función para calcular la similitud del coseno
def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# Función para encontrar la enfermedad más similar
def find_most_similar_disease(detected_disease, disease_embeddings):
    # Si la enfermedad detectada ya está en el diccionario, devolverla directamente
    if detected_disease in diseases:
        return detected_disease

    # Si no, calcular la similitud con las descripciones
    detected_embedding = generate_embedding(detected_disease)
    similarities = {
        disease: cosine_similarity(detected_embedding, embedding)
        for disease, embedding in disease_embeddings.items()
    }
    return max(similarities, key=similarities.get)


emoji_map = {
    "caries": "🦷",
    "gingivitis": "🩸",
    "cancer": "⚠️",
    "calculo": "疮",
    "placa": "❌",
    "perdidos": "❌",
    "ulceras": "⚠️"

}
# Función para generar una recomendación con Gemini
def generate_recommendation_with_gemini(disease):
    emoji = emoji_map.get(disease, "✨")  # Emoji
    prompt = (
        f"Actúa como un odontólogo profesional especializado en enfermedades dentales pero con un tono amigable y cercano, como si estuvieras chateando por WhatsApp. 😊 "
        f"Explica qué es {disease} y da consejos útiles sobre cómo tratarla o prevenirla SOLO para la enfermedad dental {disease}. Usa emojis para hacerlo más dinámico y fácil de entender. 🦷✨ "
        f"Empieza diciendo: 'Hola 👋, aquí tienes algunos consejos sobre {disease}:'. "
        f"Incluye tratamientos caseros y recuerda que no reemplazas a un profesional. 🚨"
    )
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        plain_text_recommendation = markdown.markdown(response.text.strip())
        return plain_text_recommendation
    except Exception as e:
        print(f"Error al generar la recomendación con Gemini: {e}")
        return "Ocurrió un error al generar la recomendación. Consulta a un especialista."

@app.route('/')
def index():
    return render_template('iniciocamera.html')
# Ruta para servir archivos estáticos (CSS, JS, imágenes)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No se encontró el archivo'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No se seleccionó ningún archivo'})

    # Guardar la imagen subida
    file.save(ORIGINAL_IMAGE)

    # Cargar el modelo YOLO único
    yolo_model = load_yolo_model()

    # Predicciones del modelo YOLO
    yolo_detections = process_yolo_with_selected_model(ORIGINAL_IMAGE, yolo_model)

    # Verificar si yolo_detections es un diccionario de error
    if isinstance(yolo_detections, dict) and 'error' in yolo_detections:
        return jsonify({"message": yolo_detections['error']}), 200

    if yolo_detections is None:
        return jsonify({"message": "La imagen no contiene dientes o no es válida. Intenta con otra imagen."}), 200

    # Formatear los resultados de YOLO
    yolo_results = [
        {'disease': disease, 'confidence': f"{confidence * 100:.1f}%"}
        for disease, confidence in yolo_detections
    ]

    # Obtener todas las enfermedades únicas detectadas por YOLO
    unique_diseases = set(disease for disease, _ in yolo_detections)

    # Generar recomendaciones para cada enfermedad única
    recommendations = {}
    for disease in unique_diseases:
        # Encontrar la enfermedad más similar usando embeddings
        most_similar_disease = find_most_similar_disease(disease, disease_embeddings)
        refined_recommendation = generate_recommendation_with_gemini(most_similar_disease)
        recommendations[disease] = refined_recommendation

    return jsonify({
        'original': '/static/uploads/original.jpg',
        'yolo_result': '/static/results/yolo_result.jpg',
        'yolo_detections': yolo_results,
        'recommendations': recommendations
    })


@socketio.on('message')
def handle_message(message):
    timestamp = datetime.now().strftime('%H:%M')
    emit('message', {'msg': message, 'timestamp': timestamp}, broadcast=True)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True, host='0.0.0.0', port=5000)
