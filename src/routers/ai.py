import os
import json
import torch
import cv2
import numpy as np
import albumentations as A
from albumentations.pytorch import ToTensorV2

FOLDER_PATH = "images"
MODEL_PATH = "models/UNet.pth"  # Cambiar por la ruta deseada
NUM_CLASSES = 5
OUTPUT_SIZE = (680, 382)  # width, height

# Nombres de las clases
CLASS_NAMES = {
    0: "Fondo",
    1: "Agua",
    2: "Suelo Expuesto",
    3: "Vegetacion Seca",
    4: "Vegetacion Verde"
}

# Colores en formato HEX para la visualización
CLASS_COLORS_HEX = [
    "#000000",  # 0 - Fondo
    "#004fff",  # 1 - Agua
    "#ffffff",  # 2 - Suelo Expuesto
    "#8f9107",  # 3 - Vegetación Seca
    "#08920a",  # 4 - Vegetación Verde
]

# Pipeline de preprocesamiento de imágenes
preprocess_pipeline = A.Compose([
    A.Resize(256, 256),
    A.Normalize(mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225)),
    ToTensorV2()
])


def load_segmentation_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = torch.load(MODEL_PATH, map_location=device, weights_only=False)
    model = model.to(device)
    model.eval()
    return model, device


def load_images(image_dir):
    image_list = []
    for filename in os.listdir(image_dir):
        if filename.lower().endswith((".jpg", ".JPG")):
            img_path = os.path.join(image_dir, filename)
            image = cv2.imread(img_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            augmented = preprocess_pipeline(image=image)
            tensor = augmented['image'].unsqueeze(0)
            image_list.append((filename, tensor))
    return image_list


def convert_mask_to_rgb(mask, class_colors):
    rgb_mask = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)
    for class_id, hex_color in enumerate(class_colors):
        rgb = tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        rgb_mask[mask == class_id] = rgb
    return rgb_mask


def resize_segmentation_mask(mask_rgb, target_size=OUTPUT_SIZE):
    return cv2.resize(mask_rgb, target_size, interpolation=cv2.INTER_NEAREST)


def compute_class_distribution(mask, num_classes=NUM_CLASSES, exclude_class_id=0):
    total_pixels = np.sum(mask != exclude_class_id)
    class_distribution = {}

    for class_id in range(1, num_classes):
        class_pixel_count = np.sum(mask == class_id)
        percentage = (class_pixel_count / total_pixels) * \
            100 if total_pixels > 0 else 0
        class_distribution[CLASS_NAMES[class_id]] = round(percentage, 2)

    return class_distribution


def should_discard(distribution: dict) -> bool:
    suelo = distribution.get("Suelo Expuesto", 0)
    agua = distribution.get("Agua", 0)
    seca = distribution.get("Vegetacion Seca", 0)
    verde = distribution.get("Vegetacion Verde", 0)

    # Ajustar valores
    if suelo > 50:
        return True
    if agua > 40:
        return True
    if seca == 0 and verde == 0:
        return True

    return False


def segment_folder_images(folder: str) -> bool:
    if not folder.strip():
        print("El nombre de la carpeta no fue proporcionado correctamente.")
        return False

    full_path = os.path.join(FOLDER_PATH, folder)

    if os.path.exists(os.path.join(full_path, "resultados.json")):
        print("Esta carpeta ya fue procesada anteriormente.")
        return False

    if not os.path.exists(full_path):
        print(f"La carpeta '{
              folder}' no fue encontrada en la ruta especificada.")
        return False

    model, device = load_segmentation_model()
    images = load_images(full_path)

    if not images:
        print(f"La carpeta '{
              folder}' no contiene imágenes .jpg para procesar.")
        return False

    results = []

    for filename, tensor in images:
        tensor = tensor.to(device)
        with torch.no_grad():
            output = model(tensor)
            prediction = torch.argmax(output, dim=1).squeeze().cpu().numpy()

        # Convertir la predicción a máscara RGB
        mask_rgb = convert_mask_to_rgb(prediction, CLASS_COLORS_HEX)
        mask_resized = resize_segmentation_mask(mask_rgb, OUTPUT_SIZE)

        # Extraer timestamp desde el nombre de la imagen (formato: image_<timestamp>.jpg)
        timestamp = os.path.splitext(filename)[0].replace("image_", "")

        # Crear nombre para la máscara
        output_filename = f"mask_{timestamp}.png"
        output_path = os.path.join(full_path, output_filename)

        # Guardar la máscara como imagen PNG
        cv2.imwrite(output_path, cv2.cvtColor(mask_resized, cv2.COLOR_RGB2BGR))

        # Calcular la distribución de clases
        class_distribution = compute_class_distribution(prediction)

        # Aplicar filtrado: eliminar imágenes irrelevantes
        if should_discard(class_distribution):
            os.remove(os.path.join(full_path, filename))
            os.remove(output_path)
            continue

        # Agregar resultado válido
        results.append({
            "image": filename,
            "mask": output_filename,
            "class_distribution": class_distribution,
        })

    # Guardar resultados en archivo JSON
    output_data = {
        "results": results
    }

    json_output_path = os.path.join(full_path, "resultados.json")
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    print(f"Se han procesado las imágenes en la carpeta: {folder}")
    return True
