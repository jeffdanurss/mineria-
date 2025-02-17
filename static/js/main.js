const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const cameraInput = document.getElementById('cameraInput');
const originalImage = document.getElementById('originalImage');
const progressBar = document.getElementById('progressBar');
const yoloImage = document.getElementById('yoloImage');
const customImage = document.getElementById('customImage');
const detectionResults = document.getElementById('detectionResults');
const yoloDetections = document.getElementById('yoloDetections');
const customDetections = document.getElementById('customDetections');
const recommendations = document.getElementById('recommendations');
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const captureButton = document.getElementById('captureButton');
const cameraSection = document.getElementById('cameraSection');

// Manejar selección de archivo
fileInput.onchange = () => {
    const file = fileInput.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            originalImage.src = e.target.result;
            originalImage.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    }
};

// Manejar captura desde la cámara
cameraInput.onchange = () => {
    const file = cameraInput.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            originalImage.src = e.target.result;
            originalImage.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    }
};

// Acceder a la cámara en tiempo real
let stream;
document.querySelector('label[for="cameraInput"]').addEventListener('click', async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        cameraSection.classList.remove('hidden');
    } catch (error) {
        console.error('Error al acceder a la cámara:', error);
        alert('No se pudo acceder a la cámara.');
    }
});

// Capturar fotograma desde la cámara
captureButton.addEventListener('click', () => {
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    // Mostrar la imagen capturada
    originalImage.src = canvas.toDataURL('image/jpeg');
    originalImage.classList.remove('hidden');
    // Detener la transmisión de la cámara
    if (stream) {
        const tracks = stream.getTracks();
        tracks.forEach(track => track.stop());
    }
    cameraSection.classList.add('hidden');
});

// Procesar imagen
uploadForm.onsubmit = async (e) => {
    e.preventDefault();
    progressBar.style.display = 'block';
    progressBar.style.width = '0%';
    let formData;
    if (originalImage.src.startsWith('data:image')) {
        // Si la imagen proviene de la cámara o fue seleccionada
        const blob = await fetch(originalImage.src).then(res => res.blob());
        formData = new FormData();
        formData.append('file', blob, 'captured_image.jpg');
    } else {
        // Si la imagen fue seleccionada desde archivos
        formData = new FormData(uploadForm);
    }
    let progress = 0;
    const interval = setInterval(() => {
        progress += 5;
        if (progress <= 90) {
            progressBar.style.width = progress + '%';
        }
    }, 200);
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData,
        });
        const data = await response.json();
        clearInterval(interval);
        progressBar.style.width = '100%';
        if (data.error) {
            alert(data.error);
            return;
        }
        progressBar.style.display = 'none';
        originalImage.src = data.original + '?t=' + new Date().getTime();
        yoloImage.src = data.yolo_result + '?t=' + new Date().getTime();
        customImage.src = data.custom_result + '?t=' + new Date().getTime();
        originalImage.classList.remove('hidden');
        yoloImage.classList.remove('hidden');
        customImage.classList.remove('hidden');
        detectionResults.classList.remove('hidden');
        yoloDetections.innerHTML = '';
        customDetections.innerHTML = '';
        recommendations.innerHTML = '';
        // Mostrar las detecciones y las recomendaciones
        if (data.yolo_detections && data.yolo_detections.length > 0) {
            yoloDetections.innerHTML = '';
            data.yolo_detections.forEach(detection => {
                const detectionDiv = document.createElement('div');
                detectionDiv.className = 'detection-item';
                detectionDiv.innerHTML = `
                    <div class="text-lg font-medium">Enfermedad: ${detection.disease}</div>
                    <div class="text-md text-gray-600">Nivel de Confianza: ${detection.confidence}</div>
                `;
                yoloDetections.appendChild(detectionDiv);
            });
        } else {
            yoloDetections.innerHTML = '<div class="no-detections"><p>No se han detectado enfermedades en el modelo YOLO.</p></div>';
        }
        if (data.custom_detections) {
            customDetections.innerHTML = '';
            const detectionDiv = document.createElement('div');
            detectionDiv.className = 'detection-item';
            detectionDiv.innerHTML = `
                <div class="text-lg font-medium">Enfermedad: ${data.custom_detections.disease}</div>
                <div class="text-md text-gray-600">Nivel de Confianza: ${data.custom_detections.confidence}</div>
            `;
            customDetections.appendChild(detectionDiv);
        } else {
            customDetections.innerHTML = '<div class="no-detections"><p>No se han detectado enfermedades en el modelo personalizado.</p></div>';
        }
        // Mostrar la recomendación generada por DistilGPT-2
        if (data.recommendation) {
            recommendations.innerHTML = `<p class="text-gray-600">${data.recommendation}</p>`;
        }
    } catch (error) {
        clearInterval(interval);
        progressBar.style.display = 'none';
        console.error('Error:', error);
        alert('Error al procesar la imagen.');
    }
};