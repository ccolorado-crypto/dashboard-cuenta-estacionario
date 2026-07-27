import pandas as pd
import json
from datetime import date, datetime, timedelta
import sys

def safe_float(val):
    """Convierte de forma segura los valores de coordenadas a decimales."""
    try:
        if pd.isna(val):
            return None
        return float(str(val).strip().replace(',', '.'))
    except ValueError:
        return None

def generar_dashboard():
    print("Iniciando procesamiento de datos...")
    
    try:
        df = pd.read_excel('data/data.ods', engine='odf')
    except Exception as e:
        print(f"Error crítico al leer el archivo: {e}")
        sys.exit(1)

    col_dealer = df.columns[1]
    col_fecha = df.columns[17]

    nombre_dealer_principal = str(df[col_dealer].dropna().iloc[0]) if not df[col_dealer].dropna().empty else "Dealer Principal"

    df[col_fecha] = pd.to_datetime(df[col_fecha], errors='coerce').dt.date
    
    fecha_hoy_real = date.today()
    fechas_validas = df[col_fecha].dropna()
    fechas_validas = fechas_validas[fechas_validas <= fecha_hoy_real]
    
    if not fechas_validas.empty:
        fecha_ref = fechas_validas.max()
    else:
        fecha_ref = fecha_hoy_real

    print(f"Fecha dinámica de corte utilizada: {fecha_ref}")

    records = []
    
    rule3_list = [
        "amf-25|trifasico", "amf-5|trifasico", "amf-9|trifasico", "camkit-1|análogo",
        "camkit-1|carterpillaremcp-4.2", "camkit-1|clinicamarlygen-01",
        "camkit-1|clinicamarlygen-02", "camkit-1|deepsea", "camkit-1|ps0600",
        "camkit-2|amf-25tcp/ip", "camkit-2|deepsea|trifasico|24vdc",
        "camkit-2|pcc1302-pcc1.1|trifasico|12vdc", "camkit-2|pcc1302-pcc1.1|trifasico|24vdc",
        "camkit-2|pcc2.x-3.x|trifasico|24vdc", "camkit-2|plazaamericas-gen01",
        "camkit-2|plazaamericas-gen03", "camkit-2|plazaamericas-gen04",
        "camkit-2|pso600|trifasico|12vdc", "comap amf25 electrónico",
        "modbusgenset pcc 1301/1.x/0500", "modbusgenset pcc2x3x"
    ]
    rule4_list = ["comap ws40", "comap ws40 bci", "comaps"]

    for idx, row in df.iterrows():
        tech_raw = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else "Desconocida"
        tech_clean = tech_raw.lower()
        
        if "artimo" in tech_clean or "prolub" in tech_clean:
            continue

        dealer = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else "Sin Dealer"
        cliente = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else "Sin Cliente"
        generador = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else "Sin Nombre"
        modelo_raw = str(row.iloc[6]).strip() if pd.notna(row.iloc[6]) else "Sin Modelo"
        modelo_clean = modelo_raw.lower()
        
        lat = safe_float(row.iloc[12])
        lon = safe_float(row.iloc[13])

        raw_fecha = row.iloc[17]
        fecha_str = "Sin registro"
        status = "Fuera de cobertura"
        gravity = "Sin registro previo"
        dias_offline = -1
        plan_accion = ""
        
        if pd.notna(raw_fecha):
            fecha_str = raw_fecha.strftime("%d/%m/%Y")
            if raw_fecha >= fecha_ref:
                status = "Operando"
                gravity = "Conectado"
                dias_offline = 0
            else:
                status = "Fuera de cobertura"
                dias_offline = (fecha_ref - raw_fecha).days
                if dias_offline <= 3: gravity = "1 a 3 días"
                elif dias_offline <= 7: gravity = "4 a 7 días"
                else: gravity = "Más de 7 días"

        if modelo_clean in ["exemys digital", "exemysdigital"]:
            plan_accion = "🔄 URGENTE: Servidor Exemys se apagará. Recomendado cambiar a CAMKIT2."
        elif "exemys analoga" in modelo_clean or "exemys análoga" in modelo_clean:
            plan_accion = "🔄 URGENTE: Servidor Exemys se apagará. Recomendado cambiar a COMAP AMF5."
        elif status == "Fuera de cobertura":
            if modelo_clean in rule3_list:
                plan_accion = "🛠️ Validar dispositivo, señal GPRS, añadir cable extensor."
            elif modelo_clean in rule4_list:
                plan_accion = "🔍 Validar modelo ComAp instalado. Si es 2G debe reemplazarse."
            else:
                if dias_offline <= 3:
                    plan_accion = "⚡ Intento de reinicio remoto. Verificar cortes de energía o saldo SIM."
                elif dias_offline <= 7:
                    plan_accion = "📞 Contactar cliente para validar estado físico del equipo."
                else:
                    plan_accion = "🚨 Visita técnica urgente para revisión general de hardware."
        else:
            plan_accion = "✅ Monitoreo continuo. Equipo estable."
                    
        records.append({
            "dealer": dealer,
            "generador": generador,
            "cliente": cliente,
            "tecnologia": tech_raw,
            "modelo": modelo_raw,
            "fecha": fecha_str,
            "estado": status,
            "gravedad": gravity,
            "dias_offline": dias_offline,
            "plan_accion": plan_accion,
            "lat": lat,
            "lon": lon
        })

    data_json = json.dumps(records, ensure_ascii=False)
    colombia_time = datetime.utcnow() - timedelta(hours=5)
    fecha_actualizacion = colombia_time.strftime("%d/%m/%Y a las %H:%M (Hora Col)")

    dashboard_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{nombre_dealer_principal} — Dashboard NOC ÁRTIMO</title>
    <link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root {{
            --artimo-rojo-oscuro:   #BC1818;
            --artimo-rojo-vivo:     #E10B17;
            --artimo-naranja:       #E84C22;
            --artimo-amarillo:      #F59E0B;
            --artimo-verde:         #10B981;
            
            /* Variables Light Mode */
            --bg-color: #F4F5F7;
            --card-bg: #FFFFFF;
            --text-main: #1A1A1A;
            --text-sub: #5A5A59;
            --border-color: #E5E7EB;
            --table-header: #F9FAFB;
            --table-hover: #FAFAFA;
            --tag-bg: #F2F2F2;
            --alert-bg: rgba(90,90,89,0.1);
        }}

        body.dark-mode {{
            /* Variables Dark Mode */
            --bg-color: #121212;
            --card-bg: #1E1E1E;
            --text-main: #E0E0E0;
            --text-sub: #9CA3AF;
            --border-color: #333333;
            --table-header: #2A2A2A;
            --table-hover: #2D2D2D;
            --tag-bg: #333333;
            --alert-bg: rgba(255,255,255,0.05);
        }}

        body {{ font-family: 'Open Sans', Arial, sans-serif; background: var(--bg-color); color: var(--text-main); margin: 0; padding: 0; transition: background 0.3s, color 0.3s; }}
        
        .topbar {{ background: #111; color: #FFF; min-height: 64px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; padding: 10px 24px; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 8px rgba(0,0,0,0.5); gap: 15px; }}
        .topbar-brand {{ display: flex; align-items: center; gap: 15px; flex: 1; min-width: 250px; }}
        .topbar-brand img {{ height: 48px; width: auto; object-fit: contain; }}
        .topbar-title {{ font-size: 16px; font-weight: 600; margin: 0; line-height: 1.2; }}
        .topbar-sub {{ font-size: 12px; color: #9CA3AF; margin: 0; margin-top: 2px; }}
        
        .topbar-right {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
        .filter-select {{ background: #2a2a2a; color: white; border: 1px solid #4B5563; padding: 8px 12px; border-radius: 6px; font-size: 13px; font-family: 'Open Sans'; outline: none; cursor: pointer; max-width: 200px; }}
        
        .btn-action {{ padding: 8px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; border: none; transition: opacity 0.2s; display: flex; align-items: center; gap: 6px; color: #fff; }}
        .btn-action:hover {{ opacity: 0.85; }}
        .btn-dark {{ background: #4B5563; }}
        .btn-pdf {{ background: var(--artimo-rojo-oscuro); }}
        .btn-csv {{ background: var(--artimo-verde); }}
        .btn-quick-wins {{ background: var(--artimo-rojo-vivo); font-size: 13px; padding: 10px 18px; }}

        .main-content {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}
        .alert-box {{ background: var(--alert-bg); border-left: 4px solid var(--text-sub); padding: 16px 20px; border-radius: 8px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; transition: background 0.3s; }}
        .alert-box-info p {{ margin: 0; font-size: 13px; font-weight: 600; }}
        .active-tags {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
        .tag {{ background: var(--tag-bg); color: var(--text-main); font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 12px; border: 1px solid var(--border-color); display: flex; align-items: center; gap: 6px; text-transform: uppercase; }}
        .tag button {{ background: none; border: none; color: var(--artimo-rojo-oscuro); font-weight: bold; cursor: pointer; }}
        .btn-clear {{ background: rgba(188,24,24,0.15); color: var(--artimo-rojo-oscuro); border: 1px solid rgba(188,24,24,0.3); font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 12px; cursor: pointer; }}

        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .kpi-card {{ background: var(--card-bg); border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 6px; transition: background 0.3s, border 0.3s; }}
        .kpi-card.prio-1 {{ border-top: 3px solid var(--artimo-rojo-oscuro); }}
        .kpi-card.prio-2 {{ border-top: 3px solid var(--artimo-rojo-vivo); }}
        .kpi-label {{ font-size: 12px; color: var(--text-sub); text-transform: uppercase; font-weight: 600; }}
        .kpi-value {{ font-size: 38px; font-weight: 700; line-height: 1; color: var(--text-main); }}
        .kpi-sub {{ font-size: 12px; color: var(--text-sub); }}
        .kpi-p1 .kpi-value {{ color: var(--artimo-rojo-oscuro); }}
        .kpi-p2 .kpi-value {{ color: var(--artimo-rojo-vivo); }}
        .kpi-ok .kpi-value {{ color: var(--artimo-verde); }}

        .card-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin-bottom: 24px; }}
        .card {{ background: var(--card-bg); border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 1px solid var(--border-color); transition: background 0.3s, border 0.3s; }}
        .map-card {{ grid-column: 1 / -1; padding: 15px; }}

        .table-section {{ background: var(--card-bg); border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 1px solid var(--border-color); overflow: hidden; transition: background 0.3s, border 0.3s; }}
        .table-header {{ padding: 20px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; }}
        .search-input {{ padding: 8px 12px; border: 1.5px solid var(--border-color); border-radius: 8px; font-size: 13px; width: 250px; background: transparent; color: var(--text-main); }}

        .fc-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        .fc-table th {{ background: var(--table-header); padding: 12px 20px; font-size: 11px; text-transform: uppercase; color: var(--text-sub); text-align: left; }}
        .fc-table td {{ padding: 12px 20px; border-bottom: 1px solid var(--border-color); }}
        .fc-table tr:hover td {{ background: var(--table-hover); }}

        .badge-ok {{ background: rgba(16,185,129,0.2); color: var(--artimo-verde); padding: 2px 9px; border-radius: 12px; font-size: 11px; font-weight: 600; white-space: nowrap; }}
        .badge-p1 {{ background: rgba(188,24,24,0.15); color: var(--artimo-rojo-oscuro); padding: 2px 9px; border-radius: 12px; font-size: 11px; font-weight: 600; white-space: nowrap; }}
        .badge-p2 {{ background: rgba(245,158,11,0.12); color: var(--artimo-amarillo); padding: 2px 9px; border-radius: 12px; font-size: 11px; font-weight: 600; white-space: nowrap; }}
        .badge-mid {{ background: rgba(90,90,89,0.15); color: var(--text-main); padding: 2px 9px; border-radius: 12px; font-size: 11px; font-weight: 600; white-space: nowrap; }}
        .font-bold {{ font-weight: 700; color: var(--text-main); }}
        .text-sub {{ color: var(--text-sub); font-size: 12px; }}
    </style>
</head>
<body>
    <div class="topbar">
        <div class="topbar-brand">
            <img src="artimo_logo.jpg" onerror="this.src='https://via.placeholder.com/120x40/BC1818/FFFFFF?text=ARTIMO';" alt="Logo"/>
            <div>
                <p class="topbar-title">NOC - Panel Operativo de Telemetría</p>
                <p class="topbar-sub">Actualizado: {fecha_actualizacion}</p>
            </div>
        </div>
        <div class="topbar-right">
            <button onclick="toggleDarkMode()" class="btn-action btn-dark">🌙 Tema</button>
            <select id="dealer_select" class="filter-select" onchange="filterByDropdown('dealer', this.value)">
                <option value="TODOS">-- TODOS LOS DEALERS --</option>
            </select>
            <select id="client_select" class="filter-select" onchange="filterByDropdown('cliente', this.value)">
                <option value="TODOS">-- TODOS LOS CLIENTES --</option>
            </select>
            <button onclick="exportToCSV()" class="btn-action btn-csv">📥 CSV</button>
            <button onclick="exportToPDF()" class="btn-action btn-pdf">📄 PDF</button>
        </div>
    </div>

    <div class="main-content" id="report_area">
        <div class="alert-box" data-html2canvas-ignore="true">
            <div class="alert-box-info">
                <p>Filtros Activos</p>
                <div id="active_filters" class="active-tags">
                    <span class="text-sub">Usa los menús superiores o haz clic en gráficas y mapa para filtrar.</span>
                </div>
            </div>
            <div>
                <button onclick="applyQuickWins()" class="btn-action btn-quick-wins">⚡ Victorias Rápidas (1 a 3 días)</button>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Total Generadores</div>
                <div id="kpi_total" class="kpi-value">0</div>
                <div class="kpi-sub">Equipos válidos registrados</div>
            </div>
            <div class="kpi-card kpi-ok">
                <div class="kpi-label">Conectividad</div>
                <div id="kpi_online" class="kpi-value">0%</div>
                <div class="kpi-sub">Operando actualmente</div>
            </div>
            <div class="kpi-card kpi-p1 prio-1">
                <div class="kpi-label">Equipos Offline</div>
                <div id="kpi_offline" class="kpi-value">0</div>
                <div class="kpi-sub">Fuera de cobertura</div>
            </div>
            <div class="kpi-card kpi-p2 prio-2">
                <div class="kpi-label">Días Totales Perdidos</div>
                <div id="kpi_lost_days" class="kpi-value">0</div>
                <div class="kpi-sub">Acumulado días offline</div>
            </div>
        </div>

        <div class="card-grid">
            <div class="card map-card"><div id="chart_map" style="width:100%; height:450px;"></div></div>
            
            <div class="card"><div id="chart_dona" style="width:100%;"></div></div>
            <div class="card"><div id="chart_tech" style="width:100%;"></div></div>
            <div class="card"><div id="chart_gravity" style="width:100%;"></div></div>
            <div class="card"><div id="chart_top_dealers" style="width:100%;"></div></div>
            <div class="card"><div id="chart_top_clients" style="width:100%;"></div></div>
            <div class="card"><div id="chart_top_models" style="width:100%;"></div></div>
        </div>

        <div class="table-section">
            <div class="table-header">
                <div>
                    <h2 id="table_title" style="margin:0;font-size:18px;">Detalle de Equipos</h2>
                    <span class="text-sub">Mostrando resultados filtrados.</span>
                </div>
                <div data-html2canvas-ignore="true">
                    <input type="text" id="table_search" class="search-input" placeholder="Buscar por generador..." oninput="onSearchTable(this.value)">
                </div>
            </div>
            <div style="overflow-x: auto;">
                <table class="fc-table">
                    <thead>
                        <tr>
                            <th>Dealer</th>
                            <th>Generador</th>
                            <th>Cliente</th>
                            <th>Modelo / Script</th>
                            <th>Estado</th>
                            <th>Última Conexión</th>
                            <th>Gravedad</th>
                            <th>Plan de Acción</th>
                        </tr>
                    </thead>
                    <tbody id="table_body"></tbody>
                </table>
            </div>
            <div id="no_data_message" style="display:none; padding: 40px; text-align: center; color: var(--text-sub);">
                No se encontraron registros.
            </div>
        </div>
    </div>

    <script>
        const rawData = {data_json};
        let currentFilters = {{ dealer: 'TODOS', cliente: 'TODOS', modelo: null, estado: null, tecnologia: null, gravedad: null }};
        let searchTerm = '';

        function toggleDarkMode() {{
            document.body.classList.toggle('dark-mode');
            updateDashboard(); 
        }}

        function getLayoutBase() {{
            const isDark = document.body.classList.contains('dark-mode');
            const fontColor = isDark ? '#E0E0E0' : '#1A1A1A';
            return {{
                font: {{ family: 'Open Sans, Arial, sans-serif', color: fontColor }},
                paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
                margin: {{ t: 40, b: 30, l: 40, r: 20 }}, height: 280
            }};
        }}

        function truncateLabel(str, maxLen = 22) {{
            if (!str) return '';
            return str.length > maxLen ? str.substring(0, maxLen - 2) + '..' : str;
        }}

        window.addEventListener('DOMContentLoaded', () => {{
            populateDropdowns();
            updateDashboard();
        }});

        function populateDropdowns() {{
            const dealerSelect = document.getElementById('dealer_select');
            const clientSelect = document.getElementById('client_select');
            
            dealerSelect.innerHTML = '<option value="TODOS">-- TODOS LOS DEALERS --</option>';
            clientSelect.innerHTML = '<option value="TODOS">-- TODOS LOS CLIENTES --</option>';

            const uniqueDealers = [...new Set(rawData.map(d => d.dealer))].sort();
            uniqueDealers.forEach(d => {{
                const opt = document.createElement('option');
                opt.value = opt.textContent = d;
                if(currentFilters.dealer === d) opt.selected = true;
                dealerSelect.appendChild(opt);
            }});

            let clientsData = rawData;
            if(currentFilters.dealer !== 'TODOS') {{
                clientsData = rawData.filter(d => d.dealer === currentFilters.dealer);
            }}
            const uniqueClients = [...new Set(clientsData.map(d => d.cliente))].sort();
            uniqueClients.forEach(c => {{
                const opt = document.createElement('option');
                opt.value = opt.textContent = c;
                if(currentFilters.cliente === c) opt.selected = true;
                clientSelect.appendChild(opt);
            }});
        }}

        function filterByDropdown(key, val) {{
            currentFilters[key] = val;
            if(key === 'dealer') currentFilters.cliente = 'TODOS';
            populateDropdowns(); 
            updateDashboard();
        }}

        function applyQuickWins() {{
            currentFilters = {{ dealer: 'TODOS', cliente: 'TODOS', modelo: null, estado: null, tecnologia: null, gravedad: '1 a 3 días' }};
            populateDropdowns();
            document.getElementById('table_search').value = ''; searchTerm = '';
            updateDashboard();
            document.getElementById('table_title').scrollIntoView({{ behavior: 'smooth' }});
        }}
        
        function clearFilter(key) {{
            if(key === 'dealer' || key === 'cliente') currentFilters[key] = 'TODOS';
            else currentFilters[key] = null;
            populateDropdowns();
            updateDashboard();
        }}
        
        function clearAllFilters() {{
            currentFilters = {{ dealer: 'TODOS', cliente: 'TODOS', modelo: null, estado: null, tecnologia: null, gravedad: null }};
            document.getElementById('table_search').value = ''; searchTerm = '';
            populateDropdowns();
            updateDashboard();
        }}
        
        function onSearchTable(val) {{ 
            searchTerm = val.toLowerCase().trim(); 
            renderTableOnly(); 
        }}

        function getFilteredData() {{
            return rawData.filter(d => 
                (currentFilters.dealer === 'TODOS' || d.dealer === currentFilters.dealer) &&
                (currentFilters.cliente === 'TODOS' || d.cliente === currentFilters.cliente) &&
                (!currentFilters.estado || d.estado === currentFilters.estado) &&
                (!currentFilters.tecnologia || d.tecnologia === currentFilters.tecnologia) &&
                (!currentFilters.modelo || d.modelo === currentFilters.modelo) &&
                (!currentFilters.gravedad || d.gravedad === currentFilters.gravedad)
            );
        }}

        function updateDashboard() {{
            const filteredData = getFilteredData();

            const total = filteredData.length;
            const online = filteredData.filter(d => d.estado === 'Operando').length;
            const offline = total - online;
            const lostDays = filteredData.reduce((acc, curr) => acc + (curr.dias_offline > 0 ? curr.dias_offline : 0), 0);

            document.getElementById('kpi_total').textContent = total;
            document.getElementById('kpi_online').textContent = total > 0 ? Math.round((online/total)*100) + '%' : '0%';
            document.getElementById('kpi_offline').textContent = offline;
            document.getElementById('kpi_lost_days').textContent = lostDays.toLocaleString();

            renderActiveFilterTags();
            renderMapChart(filteredData);
            renderDonaChart(filteredData);
            renderTechChart(filteredData);
            renderGravityChart(filteredData);
            renderTopDealersChart(filteredData);
            renderTopClientsChart(filteredData);
            renderTopModelsChart(filteredData);
            renderTableOnly(filteredData);
        }}

        function renderActiveFilterTags() {{
            const container = document.getElementById('active_filters');
            container.innerHTML = '';
            let has = false;
            Object.keys(currentFilters).forEach(key => {{
                if(currentFilters[key] && currentFilters[key] !== 'TODOS') {{
                    has = true;
                    container.innerHTML += `<div class="tag">${{key}}: ${{currentFilters[key]}} <button onclick="clearFilter('${{key}}')">×</button></div>`;
                }}
            }});
            if(has) container.innerHTML += `<button class="btn-clear" onclick="clearAllFilters()">Limpiar Filtros</button>`;
            else container.innerHTML = `<span class="text-sub">Usa los menús superiores o haz clic en gráficas y mapa para filtrar.</span>`;
        }}

        function renderMapChart(data) {{
            const validData = data.filter(d => d.lat !== null && d.lon !== null);
            const colorMap = {{ 'Conectado': '#10B981', '1 a 3 días': '#F59E0B', '4 a 7 días': '#E84C22', 'Más de 7 días': '#BC1818', 'Sin registro previo': '#5A5A59' }};

            const traces = [];
            const groups = [...new Set(validData.map(d => d.gravedad))];

            groups.forEach(g => {{
                const groupData = validData.filter(d => d.gravedad === g);
                traces.push({{
                    type: 'scattermapbox',
                    lat: groupData.map(d => d.lat),
                    lon: groupData.map(d => d.lon),
                    mode: 'markers',
                    marker: {{ size: 10, color: colorMap[g] || '#5A5A59' }},
                    name: g,
                    customdata: groupData.map(d => d.generador), 
                    text: groupData.map(d => `<b>${{d.generador}}</b><br>Cliente: ${{d.cliente}}<br><i>Clic para filtrar tabla</i>`),
                    hoverinfo: 'text'
                }});
            }});

            const layout = {{
                ...getLayoutBase(),
                height: 450,
                title: {{ text: '<b>Ubicación de Equipos (Clic en punto para buscar)</b>', font: {{size: 16}}, x: 0.5 }},
                mapbox: {{ style: 'open-street-map', center: {{lat: 4.5709, lon: -74.2973}}, zoom: 4.5 }},
                showlegend: true, legend: {{ orientation: 'h', y: -0.1 }}, margin: {{ t: 50, b: 20, l: 10, r: 10 }}
            }};

            Plotly.react('chart_map', traces, layout, {{ responsive: true, displayModeBar: false }});
            
            document.getElementById('chart_map').removeAllListeners('plotly_click');
            document.getElementById('chart_map').on('plotly_click', d => {{
                const clickedGen = d.points[0].customdata;
                document.getElementById('table_search').value = clickedGen;
                onSearchTable(clickedGen);
                document.getElementById('table_title').scrollIntoView({{ behavior: 'smooth' }});
            }});
        }}

        function renderDonaChart(data) {{
            const op = data.filter(d => d.estado === 'Operando').length;
            const off = data.filter(d => d.estado === 'Fuera de cobertura').length;
            const layout = {{ ...getLayoutBase(), title: {{ text: '<b>Estado General</b>', font: {{size: 15}}, x: 0.5 }}, legend: {{ orientation: 'h', y: -0.1 }} }};
            Plotly.react('chart_dona', [{{ values: [op, off], labels: ['Operando', 'Fuera de cobertura'], type: 'pie', hole: 0.5, marker: {{ colors: ['#10B981', '#BC1818'] }}, textinfo: 'value+percent' }}], layout, {{ responsive: true, displayModeBar: false }});
            document.getElementById('chart_dona').removeAllListeners('plotly_click');
            document.getElementById('chart_dona').on('plotly_click', d => {{ currentFilters.estado = (currentFilters.estado === d.points[0].label) ? null : d.points[0].label; updateDashboard(); }});
        }}

        function renderTechChart(data) {{
            const map = {{}};
            data.forEach(d => {{
                if(!map[d.tecnologia]) map[d.tecnologia] = {{ op: 0, off: 0 }};
                d.estado === 'Operando' ? map[d.tecnologia].op++ : map[d.tecnologia].off++;
            }});
            const x = Object.keys(map).sort();
            const layout = {{ ...getLayoutBase(), title: {{ text: '<b>Estado por Tecnología</b>', font: {{size: 15}}, x: 0.5 }}, barmode: 'group', legend: {{ orientation: 'h', y: -0.2 }} }};
            Plotly.react('chart_tech', [ {{ x: x, y: x.map(k=>map[k].op), name: 'Operando', type: 'bar', marker: {{ color: '#10B981' }} }}, {{ x: x, y: x.map(k=>map[k].off), name: 'Offline', type: 'bar', marker: {{ color: '#BC1818' }} }} ], layout, {{ responsive: true, displayModeBar: false }});
            document.getElementById('chart_tech').removeAllListeners('plotly_click');
            document.getElementById('chart_tech').on('plotly_click', d => {{ currentFilters.tecnologia = (currentFilters.tecnologia === d.points[0].x) ? null : d.points[0].x; updateDashboard(); }});
        }}

        function renderGravityChart(data) {{
            const map = {{ "1 a 3 días": 0, "4 a 7 días": 0, "Más de 7 días": 0, "Sin registro previo": 0 }};
            data.filter(d => d.estado !== 'Operando').forEach(d => {{ if(map[d.gravedad] !== undefined) map[d.gravedad]++; }});
            const x = Object.keys(map);
            const layout = {{ ...getLayoutBase(), title: {{ text: '<b>Gravedad (Mejor a Peor)</b>', font: {{size: 15}}, x: 0.5 }} }};
            Plotly.react('chart_gravity', [{{ x: x, y: x.map(k=>map[k]), type: 'bar', marker: {{ color: ['#F59E0B', '#E84C22', '#BC1818', '#5A5A59'] }} }}], layout, {{ responsive: true, displayModeBar: false }});
            document.getElementById('chart_gravity').removeAllListeners('plotly_click');
            document.getElementById('chart_gravity').on('plotly_click', d => {{ currentFilters.gravedad = (currentFilters.gravedad === d.points[0].x) ? null : d.points[0].x; updateDashboard(); }});
        }}

        function renderTopDealersChart(data) {{
            const map = {{}};
            data.filter(d => d.estado !== 'Operando').forEach(d => map[d.dealer] = (map[d.dealer]||0) + 1);
            const sorted = Object.entries(map).sort((a,b)=>b[1]-a[1]).slice(0,10).reverse();
            
            const layout = {{ 
                ...getLayoutBase(), 
                title: {{ text: '<b>Top Dealers (Offline)</b>', font: {{size: 15}}, x: 0.5 }}, 
                margin: {{ t:40, b:30, l:170, r:20 }}
            }};
            
            Plotly.react('chart_top_dealers', [{{ 
                y: sorted.map(i=>truncateLabel(i[0], 25)), 
                x: sorted.map(i=>i[1]), 
                type: 'bar', orientation: 'h', marker: {{ color: '#BC1818' }},
                text: sorted.map(i=>i[0]), 
                textposition: 'none', // Esta es la línea que oculta el texto sobre la barra
                hoverinfo: 'text+x' 
            }}], layout, {{ responsive: true, displayModeBar: false }});
            
            document.getElementById('chart_top_dealers').removeAllListeners('plotly_click');
            document.getElementById('chart_top_dealers').on('plotly_click', d => {{
                filterByDropdown('dealer', (currentFilters.dealer === d.points[0].text) ? 'TODOS' : d.points[0].text);
            }});
        }}

        function renderTopClientsChart(data) {{
            const map = {{}};
            data.filter(d => d.estado !== 'Operando').forEach(d => map[d.cliente] = (map[d.cliente]||0) + 1);
            const sorted = Object.entries(map).sort((a,b)=>b[1]-a[1]).slice(0,10).reverse();
            
            const layout = {{ 
                ...getLayoutBase(), 
                title: {{ text: '<b>Top Clientes (Offline)</b>', font: {{size: 15}}, x: 0.5 }}, 
                margin: {{ t:40, b:30, l:170, r:20 }} 
            }};
            
            Plotly.react('chart_top_clients', [{{ 
                y: sorted.map(i=>truncateLabel(i[0], 25)), 
                x: sorted.map(i=>i[1]), 
                type: 'bar', orientation: 'h', marker: {{ color: '#E84C22' }},
                text: sorted.map(i=>i[0]), 
                textposition: 'none', // Oculta el texto sobre la barra
                hoverinfo: 'text+x'
            }}], layout, {{ responsive: true, displayModeBar: false }});
            
            document.getElementById('chart_top_clients').removeAllListeners('plotly_click');
            document.getElementById('chart_top_clients').on('plotly_click', d => {{
                filterByDropdown('cliente', (currentFilters.cliente === d.points[0].text) ? 'TODOS' : d.points[0].text);
            }});
        }}

        function renderTopModelsChart(data) {{
            const map = {{}};
            data.filter(d => d.estado !== 'Operando').forEach(d => map[d.modelo] = (map[d.modelo]||0) + 1);
            const sorted = Object.entries(map).sort((a,b)=>b[1]-a[1]).slice(0,10).reverse();
            
            const layout = {{ 
                ...getLayoutBase(), 
                title: {{ text: '<b>Top Modelos/Scripts (Offline)</b>', font: {{size: 15}}, x: 0.5 }}, 
                margin: {{ t:40, b:30, l:170, r:20 }} 
            }};
            
            Plotly.react('chart_top_models', [{{ 
                y: sorted.map(i=>truncateLabel(i[0], 25)), 
                x: sorted.map(i=>i[1]), 
                type: 'bar', orientation: 'h', marker: {{ color: '#F59E0B' }},
                text: sorted.map(i=>i[0]), 
                textposition: 'none', // Oculta el texto sobre la barra
                hoverinfo: 'text+x'
            }}], layout, {{ responsive: true, displayModeBar: false }});
            
            document.getElementById('chart_top_models').removeAllListeners('plotly_click');
            document.getElementById('chart_top_models').on('plotly_click', d => {{
                currentFilters.modelo = (currentFilters.modelo === d.points[0].text) ? null : d.points[0].text;
                updateDashboard();
            }});
        }}

        function renderTableOnly(dataToRender) {{
            const data = dataToRender || getFilteredData();
            const tbody = document.getElementById('table_body');
            const msg = document.getElementById('no_data_message');
            
            let finalData = data.filter(d => d.generador.toLowerCase().includes(searchTerm));
            finalData.sort((a, b) => b.dias_offline - a.dias_offline);
            
            if(finalData.length === 0) {{ tbody.innerHTML = ''; msg.style.display = 'block'; return; }}
            msg.style.display = 'none';

            let tableHTML = '';
            finalData.forEach(r => {{
                const statusBadge = r.estado === 'Operando' ? '<span class="badge-ok">Operando</span>' : '<span class="badge-p1">Offline</span>';
                let gravBadge = '<span class="badge-ok">Estable</span>';
                if(r.estado !== 'Operando') {{
                    if(r.gravedad === '1 a 3 días') gravBadge = '<span class="badge-p2">1 a 3 días</span>';
                    else if(r.gravedad === 'Más de 7 días') gravBadge = '<span class="badge-p1">Más de 7 días</span>';
                    else gravBadge = `<span class="badge-mid">${{r.gravedad}}</span>`;
                }}
                
                tableHTML += `<tr>
                    <td class="text-sub">${{r.dealer}}</td>
                    <td class="font-bold">${{r.generador}}</td>
                    <td class="text-sub">${{r.cliente}}</td>
                    <td class="text-sub">${{r.modelo}}</td>
                    <td>${{statusBadge}}</td>
                    <td class="text-sub">${{r.fecha}}</td>
                    <td>${{gravBadge}}</td>
                    <td><strong style="font-size:12px;">${{r.plan_accion}}</strong></td>
                </tr>`;
            }});
            tbody.innerHTML = tableHTML;
        }}
        
        function exportToCSV() {{
            const dataToExport = getFilteredData().filter(d => d.generador.toLowerCase().includes(searchTerm));
            if (dataToExport.length === 0) return alert("No hay datos para exportar.");

            const headers = ["Dealer", "Generador", "Cliente", "Tecnologia", "Modelo_Script", "Estado", "Ultima_Conexion", "Severidad", "Dias_Desconectado", "Latitud", "Longitud", "Plan_de_Accion"];
            const csvRows = [headers.join(',')];

            dataToExport.forEach(r => {{
                const latStr = r.lat !== null ? r.lat : '';
                const lonStr = r.lon !== null ? r.lon : '';
                const values = [ `"${{r.dealer}}"`, `"${{r.generador}}"`, `"${{r.cliente}}"`, `"${{r.tecnologia}}"`, `"${{r.modelo}}"`, `"${{r.estado}}"`, `"${{r.fecha}}"`, `"${{r.gravedad}}"`, r.dias_offline, latStr, lonStr, `"${{r.plan_accion}}"` ];
                csvRows.push(values.join(','));
            }});

            const blob = new Blob(["\\uFEFF" + csvRows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.setAttribute('href', url);
            a.setAttribute('download', `Artimo_Equipos_${{new Date().getTime()}}.csv`);
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }}

        function exportToPDF() {{
            const element = document.getElementById('report_area');
            const opt = {{
                margin:       0.3,
                filename:     `Reporte_Artimo_${{new Date().getTime()}}.pdf`,
                image:        {{ type: 'jpeg', quality: 0.98 }},
                html2canvas:  {{ scale: 2, useCORS: true }},
                jsPDF:        {{ unit: 'in', format: 'a4', orientation: 'landscape' }}
            }};
            html2pdf().set(opt).from(element).save();
        }}
    </script>
</body>
</html>"""

    html_final = dashboard_html.replace('{data_json}', data_json)
    with open('dashboard_conectividad.html', 'w', encoding='utf-8') as f:
        f.write(html_final)
    print("Dashboard final actualizado: Error de superposición de texto en gráficas de barras solucionado.")

if __name__ == "__main__":
    generar_dashboard()
