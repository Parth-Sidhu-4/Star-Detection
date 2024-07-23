import requests
import cv2
import random
import numpy as np

# Flickr API key and album ID
flickr_api_key = "671e6707a8352bc16968a743b8bac60e"
album_id = "72157698290709165"


def fetch_image_urls(album_id, api_key):
    """Fetch image URLs from NASA's Hubble's Star Clusters Flickr album."""
    api_url = f"https://www.flickr.com/services/rest/?method=flickr.photosets.getPhotos&api_key={api_key}&photoset_id={album_id}&format=json&nojsoncallback=1"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        if "photoset" in data and "photo" in data["photoset"]:
            return [
                f"https://farm{photo['farm']}.staticflickr.com/{photo['server']}/{photo['id']}_{photo['secret']}_b.jpg"
                for photo in data["photoset"]["photo"]
            ]
    except requests.RequestException as e:
        print(f"Error fetching images: {e}")
    return []


def download_image(image_url, file_path):
    """Download an image from a URL and save it to a file."""
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    except requests.RequestException as e:
        print(f"Error downloading image: {e}")


def enhance_contrast(image):
    """Enhance the contrast of the image using histogram equalization."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)


def apply_morphological_operations(binary_image, kernel):
    """Apply morphological operations to the binary image."""
    dilated_image = cv2.dilate(binary_image, kernel, iterations=1)
    eroded_image = cv2.erode(dilated_image, kernel, iterations=1)
    return eroded_image


def find_contours(eroded_image):
    """Find contours in the eroded image."""
    contours, _ = cv2.findContours(
        eroded_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    return contours


def detect_stars(image_path):
    """Detect stars in an image and return their coordinates."""
    image = cv2.imread(image_path)
    enhanced_image = enhance_contrast(image)
    gray_image = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2GRAY)
    blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)

    binary_image = cv2.adaptiveThreshold(
        blurred_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )

    kernel = np.ones((3, 3), np.uint8)
    eroded_image = apply_morphological_operations(binary_image, kernel)
    contours = find_contours(eroded_image)

    blob_detector_params = cv2.SimpleBlobDetector_Params()
    blob_detector_params.filterByArea = True
    blob_detector_params.minArea = 5
    blob_detector = cv2.SimpleBlobDetector_create(blob_detector_params)
    detected_blobs = blob_detector.detect(eroded_image)

    star_coordinates = set()

    for contour in contours:
        if cv2.contourArea(contour) > 10:
            moments = cv2.moments(contour)
            if moments["m00"] != 0:
                center_x = int(moments["m10"] / moments["m00"])
                center_y = int(moments["m01"] / moments["m00"])
                star_coordinates.add((center_x, center_y))

    star_coordinates.update(
        (int(blob.pt[0]), int(blob.pt[1])) for blob in detected_blobs
    )

    return list(star_coordinates)


def overlay_results(original_image_path, detected_stars, output_image_path):
    """Overlay detected stars and information text onto the image."""
    image = cv2.imread(original_image_path)
    annotated_image = image.copy()

    for x, y in detected_stars:
        cv2.circle(annotated_image, (x, y), 5, (0, 255, 255), 2)

    star_count = len(detected_stars)
    note_text = "Note: The detection may miss very shiny or sparkling stars (plus other errors there too)!"
    count_text = f"Number of stars detected: {star_count}"
    combined_text = f"{note_text}\n{count_text}"

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    font_color = (203, 192, 255)
    text_thickness = 2
    outline_thickness = 4
    line_type = cv2.LINE_AA

    y_offset = 30  # Initial y_offset
    for line in combined_text.split("\n"):
        # Outline
        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            cv2.putText(
                annotated_image,
                line,
                (10 + dx, y_offset + dy),
                font,
                font_scale,
                (0, 0, 0),
                outline_thickness,
                line_type,
            )
        # Text
        cv2.putText(
            annotated_image,
            line,
            (10, y_offset),
            font,
            font_scale,
            font_color,
            text_thickness,
            line_type,
        )
        y_offset += 30  # Move to next line

    cv2.imwrite(output_image_path, annotated_image, [cv2.IMWRITE_PNG_COMPRESSION, 0])


def main():
    image_urls = fetch_image_urls(album_id, flickr_api_key)

    if not image_urls:
        print("No images found.")
        return

    selected_image_url = random.choice(image_urls)
    print(f"Selected image: {selected_image_url}")

    original_image_path = "original_image.jpg"
    download_image(selected_image_url, original_image_path)

    star_positions = detect_stars(original_image_path)
    final_output_path = "final_result.png"
    overlay_results(original_image_path, star_positions, final_output_path)

    final_image = cv2.imread(final_output_path)
    cv2.namedWindow("Final Result", cv2.WINDOW_NORMAL)
    cv2.imshow("Final Result", final_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
