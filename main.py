from flask import Flask, request, jsonify
from flask_cors import CORS  # Para permitir acceso desde cualquier dominio
import pdfplumber
import re
import os

app = Flask(__name__)
CORS(app)  # Permitir acceso desde cualquier dominio

def procesar_pdf(ruta_pdf):
    datos = {}
    nivel_actual = None
    grupo_actual = None
    plan_actual = None
    clave_grupo = None  

    with pdfplumber.open(ruta_pdf) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            
            for table in tables:
                for row in table:
                    row = [celda.strip() if isinstance(celda, str) else None for celda in row]
                    
                    if "Plan:" in str(row):
                        for celda in row:
                            if celda and "Plan:" in celda:
                                plan_actual = celda.split("Plan:")[1].strip()
                            if celda and "Nivel:" in celda:
                                nivel_actual = celda.split("Nivel:")[1].strip()
                            if celda and "Grupo:" in celda:
                                grupo_actual = celda.split("Grupo:")[1].strip().replace(" ", "")
                        
                        if nivel_actual and grupo_actual:
                            clave_grupo = f"Nivel_{nivel_actual}_Grupo_{grupo_actual}"
                            if clave_grupo not in datos:
                                datos[clave_grupo] = {
                                    "Plan": plan_actual,
                                    "Nivel": nivel_actual,
                                    "Grupo": grupo_actual,
                                    "Horario": []
                                }
                        continue
                    
                    if any("pm" in str(celda).lower() or "am" in str(celda).lower() for celda in row) and len(row) >= 7:
                        horas = row[0]
                        if not horas:
                            continue
                            
                        dias = {
                            "LUNES": row[1],
                            "MARTES": row[2],
                            "MIÉRCOLES": row[3],
                            "JUEVES": row[4],
                            "VIERNES": row[5],
                            "SÁBADO": row[6]
                        }
                        
                        for dia, materia in dias.items():
                            if materia and materia.lower() != "none":
                                materia_limpia = re.sub(r'\s+', ' ', materia).strip()
                                materia_nombre = re.sub(r'\b[A-Z]\d-\d{3} AULA\b', '', materia_limpia, flags=re.IGNORECASE)
                                materia_nombre = materia_nombre.replace("VIRTUAL", "").strip()
                                aula_match = re.search(r'\b[A-Z]\d-\d{3} AULA\b.*', materia_limpia, flags=re.IGNORECASE)
                                aula = aula_match.group() if aula_match else "No especificado"
                                
                                if clave_grupo in datos:
                                    datos[clave_grupo]["Horario"].append({
                                        "Dia": dia,
                                        "Hora": horas,
                                        "Materia": materia_nombre,
                                        "Aula": aula,
                                        "Modalidad": "Virtual" if "VIRTUAL" in materia_limpia.upper() else "Presencial"
                                    })
    
    return datos

@app.route('/procesar', methods=['POST'])
def procesar():
    if 'archivo' not in request.files:
        return jsonify({"error": "No se proporcionó un archivo"}), 400
    
    archivo = request.files['archivo']
    
    if archivo.filename == '':
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    
    ruta_temporal = f"temp_{archivo.filename}"
    archivo.save(ruta_temporal)

    try:
        datos = procesar_pdf(ruta_temporal)
        os.remove(ruta_temporal)  
        return jsonify(datos)
    except Exception as e:
        os.remove(ruta_temporal)  
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)  # Escuchar en todas las IPs
