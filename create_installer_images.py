from PIL import Image, ImageDraw, ImageFont
import os

def create_bmp(width, height, text, output_path):
    # Crear imagen negra
    image = Image.new('RGB', (width, height), 'black')
    draw = ImageDraw.Draw(image)
    
    try:
        # Intentar cargar una fuente del sistema
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        # Si falla, usar la fuente por defecto
        font = ImageFont.load_default()
    
    # Obtener dimensiones del texto
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Calcular posición central
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Dibujar texto en blanco
    draw.text((x, y), text, fill='white', font=font)
    
    # Guardar como BMP
    image.save(output_path, 'BMP')

def main():
    # Asegurar que existe el directorio assets
    os.makedirs('assets', exist_ok=True)
    
    # Crear imagen de bienvenida (164x314)
    create_bmp(164, 314, 'Sound to XML\nConverter', 'assets/installer_welcome.bmp')
    
    # Crear imagen de encabezado (150x57)
    create_bmp(150, 57, 'Sound to XML', 'assets/installer_header.bmp')

if __name__ == '__main__':
    main() 