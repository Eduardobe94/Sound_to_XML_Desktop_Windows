from PIL import Image, ImageDraw
import os
import math

def create_logo():
    sizes = {
        'ico': [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        'icns': [(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)]
    }
    
    def create_spiral_points(cx, cy, start_radius, end_radius, steps):
        points = []
        for i in range(steps):
            angle = i * math.pi * 2 / steps
            radius = start_radius + (end_radius - start_radius) * i / steps
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            points.append((x, y))
        return points
    
    def create_base_logo(size):
        # Crear imagen con fondo negro
        image = Image.new('RGBA', size, (0, 0, 0, 255))
        draw = ImageDraw.Draw(image)
        
        # Colores
        tech_blue = (0, 174, 239, 255)    # #00AEEF - Azul tecnológico
        neon_purple = (170, 70, 255, 255) # #AA46FF - Púrpura neón
        
        width, height = size
        center_x, center_y = width/2, height/2
        
        # Dibujar espirales de IA
        spiral_points = create_spiral_points(center_x, center_y, width*0.1, width*0.4, 180)
        for i in range(len(spiral_points)-1):
            alpha = int(255 * (1 - i/len(spiral_points)))
            color = (tech_blue[0], tech_blue[1], tech_blue[2], alpha)
            draw.line([spiral_points[i], spiral_points[i+1]], fill=color, width=max(1, int(width*0.005)))
        
        # Área para el logo KU
        padding = width * 0.2
        logo_size = width - (padding * 2)
        
        # K estilizada
        k_width = logo_size * 0.4
        k_height = logo_size * 0.5
        k_x = padding + (logo_size * 0.15)
        k_y = padding + (logo_size * 0.25)
        
        # Línea vertical de la K
        draw.rectangle(
            [k_x, k_y, k_x + k_width*0.25, k_y + k_height],
            fill=neon_purple
        )
        
        # Diagonales de la K con efecto tech
        points_upper = [
            (k_x + k_width*0.2, k_y),
            (k_x + k_width*1.1, k_y),
            (k_x + k_width*0.65, k_y + k_height/2),
            (k_x + k_width*0.2, k_y + k_height/2)
        ]
        
        points_lower = [
            (k_x + k_width*0.2, k_y + k_height/2),
            (k_x + k_width*0.65, k_y + k_height/2),
            (k_x + k_width*1.1, k_y + k_height),
            (k_x + k_width*0.2, k_y + k_height)
        ]
        
        draw.polygon(points_upper, fill=tech_blue)
        draw.polygon(points_lower, fill=tech_blue)
        
        # U futurista
        u_width = logo_size * 0.3
        u_height = logo_size * 0.5
        u_x = padding + (logo_size * 0.55)
        u_y = padding + (logo_size * 0.25)
        
        # Líneas verticales de la U
        draw.rectangle(
            [u_x, u_y, u_x + u_width*0.3, u_y + u_height],
            fill=neon_purple
        )
        draw.rectangle(
            [u_x + u_width*0.7, u_y, u_x + u_width, u_y + u_height],
            fill=neon_purple
        )
        
        # Base curva de la U
        draw.ellipse(
            [u_x, u_y + u_height - u_width*0.3,
             u_x + u_width, u_y + u_height + u_width*0.3],
            fill=tech_blue
        )
        
        # Puntos de conexión (efecto tech)
        dot_size = width * 0.01
        for x, y in [
            (k_x, k_y), (k_x + k_width, k_y),
            (u_x, u_y), (u_x + u_width, u_y),
            (k_x + k_width*0.5, k_y + k_height),
            (u_x + u_width*0.5, u_y + u_height)
        ]:
            draw.ellipse(
                [x - dot_size, y - dot_size, x + dot_size, y + dot_size],
                fill=tech_blue
            )
        
        return image
    
    os.makedirs('icons', exist_ok=True)
    
    # Generar iconos
    ico_images = []
    for size in sizes['ico']:
        ico_images.append(create_base_logo(size))
    
    ico_path = os.path.join('icons', 'icon.ico')
    ico_images[0].save(ico_path, format='ICO', sizes=sizes['ico'])
    
    icns_path = os.path.join('icons', 'icon.icns')
    icns_image = create_base_logo((1024, 1024))
    icns_image.save(icns_path, format='ICNS')
    
    print(f"✅ Iconos generados en la carpeta 'icons':")
    print(f"   - Windows: {ico_path}")
    print(f"   - macOS: {icns_path}")

if __name__ == "__main__":
    create_logo() 