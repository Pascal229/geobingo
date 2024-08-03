from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import json
from geo_analyzer import GeoAnalyzer
from shapely.geometry import Point
import numpy as np
from shapely.geometry.polygon import Polygon


class PDFGenerator:
    def __init__(self):
        self.geo_analyzer = GeoAnalyzer()

    def generate_pdf(self):
        self.geo_analyzer.compute_ellipse_and_plot()

        ellipse_center = np.mean([coords for coords in self.geo_analyzer.boundary_coords.values()], axis=0)
        boundary_latitudes = [coords[0] for coords in self.geo_analyzer.boundary_coords.values()]
        boundary_longitudes = [coords[1] for coords in self.geo_analyzer.boundary_coords.values()]
        boundary_radius_lat = (max(boundary_latitudes) - min(boundary_latitudes)) / 2
        boundary_radius_lon = (max(boundary_longitudes) - min(boundary_longitudes)) / 2

        polygon_points = [
            (ellipse_center[0] + boundary_radius_lat * np.cos(theta), ellipse_center[1] + boundary_radius_lon * np.sin(theta))
            for theta in np.linspace(0, 2 * np.pi, 100)
        ]
        polygon = Polygon(polygon_points)

        with open('locations.json', 'r') as f:
            locations = json.load(f)

        grouped_locations = {}
        for loc in locations:
            loc_type = loc.get('type')
            label = loc.get('label', 'N/A')
            search_string = loc.get('searchString', 'N/A')

            if loc_type == 'place':
                coords = self.geo_analyzer.get_coordinates(search_string)
                if coords:
                    point = Point(coords[0], coords[1])
                    inside_area = polygon.contains(point)
                    status = 'Inside' if inside_area else 'Outside'
                else:
                    status = 'Not Found'
            else:
                status = 'N/A'

            if loc_type not in grouped_locations:
                grouped_locations[loc_type] = []
            grouped_locations[loc_type].append({
                'label': label,
                'status': status
            })

        pdf_filename = 'report.pdf'
        doc = SimpleDocTemplate(pdf_filename, pagesize=letter)

        title_style = ParagraphStyle(name='TitleStyle', fontSize=16, fontName='Helvetica-Bold', spaceAfter=12, alignment=1)
        normal_style = ParagraphStyle(name='NormalStyle', fontSize=12, fontName='Helvetica', spaceAfter=6)
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), '#f0f0f0'),
            ('GRID', (0, 0), (-1, -1), 0.5, 'black'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONT', (0, 1), (-1, -1), 'Helvetica'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), '#ffffff')
        ])

        content = []

        column_width = (doc.width - 30) / 2

        def create_table(data):
            table = Table(data, colWidths=[column_width])
            table.setStyle(table_style)
            return table

        def create_page_for_types(types):
            content.append(Spacer(1, 24))
            for loc_type in types:
                title = Paragraph(f"<b>{loc_type.capitalize()}</b>", title_style)
                content.append(title)
                content.append(Spacer(1, 12))

                data = []
                for item in grouped_locations.get(loc_type, []):
                    label = item['label']
                    status = item['status']
                    if status == 'N/A':
                        text = label
                    else:
                        text = f"{label} ({status})"
                    data.append([text])
                
                table = create_table(data)
                content.append(table)
                content.append(Spacer(1, 24))

        types = list(grouped_locations.keys())
        if len(types) > 1:
            half = len(types) // 2
            create_page_for_types(types[:half])
            create_page_for_types(types[half:])
        else:
            create_page_for_types(types)

        doc.build(content)
        print(f"PDF report generated: {pdf_filename}")

if __name__ == "__main__":
    pdf_generator = PDFGenerator()
    pdf_generator.generate_pdf()
