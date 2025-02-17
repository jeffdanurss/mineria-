import os
import pandas as pd
import shutil  # Para mover archivos

# Configuración
DATASET_DIR = "C:/Users/HP VICTUS/Downloads/train/train"
OUTPUT_DIR = "C:/dataset"  # Carpeta donde se organizarán los datos
CLASSES = ["cancer", "caries", "gingivitis", "perdidos", "ulceras"]
label_map = {cls: idx for idx, cls in enumerate(CLASSES)}

def normalize_class_name(class_name):
    """
    Normaliza los nombres de las clases para manejar variantes.
    Por ejemplo, convierte 'perdido' a 'perdidos' y 'ulcera' a 'ulceras'.
    """
    if class_name == "perdido":
        return "perdidos"
    if class_name == "ulcera":
        return "ulceras"
    return class_name

def organize_and_convert_to_yolo(dataset_dir, output_dir, classes):
    # Crear carpetas de salida
    images_dir = os.path.join(output_dir, "images")
    labels_dir = os.path.join(output_dir, "labels")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)

    for class_name in classes:
        annotations_file = os.path.join(dataset_dir, class_name, "_annotations.csv")
        if not os.path.exists(annotations_file):
            print(f"Archivo de anotaciones no encontrado: {annotations_file}")
            continue

        annotations = pd.read_csv(annotations_file)
        for _, row in annotations.iterrows():
            filename = row['filename']
            width = row['width']
            height = row['height']
            class_name = row['class']

            # Normalizar el nombre de la clase
            normalized_class_name = normalize_class_name(class_name)

            # Verificar si la clase normalizada está en el label_map
            if normalized_class_name not in label_map:
                print(f"Clase desconocida encontrada: {class_name}")
                continue

            xmin, ymin, xmax, ymax = row['xmin'], row['ymin'], row['xmax'], row['ymax']

            # Calcular valores normalizados para YOLO
            x_center = (xmin + xmax) / 2 / width
            y_center = (ymin + ymax) / 2 / height
            bbox_width = (xmax - xmin) / width
            bbox_height = (ymax - ymin) / height

            # Guardar en formato YOLO
            label_id = label_map[normalized_class_name]
            txt_filename = os.path.splitext(filename)[0] + ".txt"
            with open(os.path.join(labels_dir, txt_filename), "a") as f:
                f.write(f"{label_id} {x_center} {y_center} {bbox_width} {bbox_height}\n")

            # Mover la imagen a la carpeta /images
            src_image_path = os.path.join(dataset_dir, class_name, filename)
            dst_image_path = os.path.join(images_dir, filename)
            if os.path.exists(src_image_path):
                shutil.copy(src_image_path, dst_image_path)  # Copiar la imagen
            else:
                print(f"Imagen no encontrada: {src_image_path}")

    print("Organización y conversión completadas.")

# Ejecutar la función
organize_and_convert_to_yolo(DATASET_DIR, OUTPUT_DIR, CLASSES)