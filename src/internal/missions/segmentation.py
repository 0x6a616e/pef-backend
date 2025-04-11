import albumentations as A
from albumentations.pytorch import ToTensorV2
import cv2
import numpy as np
import os
import torch

from .config import settings
from .models import Result, SegmentationClass


def load_segmentation_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = torch.load(settings.model_path,
                       map_location=device, weights_only=False)
    model = model.to(device)
    model.eval()
    return model, device


preprocess_pipeline = A.Compose([
    A.Resize(256, 256),
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ToTensorV2()
])


def load_images(foldername: str):
    image_list = []
    folder_path = os.path.join(settings.images_folder, foldername)
    for filename in os.listdir(folder_path):
        if filename.startswith("drone"):
            img_path = os.path.join(folder_path, filename)
            image = cv2.imread(img_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            augmented = preprocess_pipeline(image=image)
            tensor = augmented['image'].unsqueeze(0)
            image_list.append((filename, tensor))
    return image_list


def convert_mask_to_rgb(mask):
    rgb_mask = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)
    for segmentation_class in SegmentationClass:
        red = int(segmentation_class.color[1:3], 16)
        green = int(segmentation_class.color[3:5], 16)
        blue = int(segmentation_class.color[5:7], 16)
        rgb_mask[mask == int(segmentation_class.value)] = (red, green, blue)
    return rgb_mask


def resize_segmentation_mask(mask_rgb):
    return cv2.resize(
        mask_rgb,
        settings.image_size,
        interpolation=cv2.INTER_NEAREST
    )


def compute_class_distribution(mask, exclude_class=SegmentationClass.FONDO):
    total_pixels = np.sum(mask != int(exclude_class.value))
    class_distribution = {}

    for segmentation_class in SegmentationClass:
        class_pixel_count = np.sum(mask == int(segmentation_class.value))
        percentage = (class_pixel_count / total_pixels) * \
            100 if total_pixels > 0 else 0
        class_distribution[segmentation_class.value] = round(percentage, 2)

    return class_distribution


def segment_folder(foldername: str) -> list[Result]:
    model, device = load_segmentation_model()
    images = load_images(foldername)

    results: list[Result] = []

    for filename, tensor in images:
        tensor = tensor.to(device)
        with torch.no_grad():
            output = model(tensor)
            prediction = torch.argmax(output, dim=1).squeeze().cpu().numpy()
        mask_rgb = convert_mask_to_rgb(prediction)
        mask_resized = resize_segmentation_mask(mask_rgb)
        filedata = "_".join(filename.split("_")[1:-1])
        mask_filename = f"mask_{filedata}_.png"
        output_path = os.path.join(
            settings.images_folder,
            foldername,
            mask_filename
        )
        cv2.imwrite(output_path, cv2.cvtColor(mask_resized, cv2.COLOR_RGB2BGR))
        class_distribution = compute_class_distribution(prediction)
        results.append(
            Result(
                image=filename,
                mask=mask_filename,
                distribution=class_distribution
            )
        )

    return results
