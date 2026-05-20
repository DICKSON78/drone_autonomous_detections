import sys, time, socket, threading, json, math, random, os
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, '/home/dickson/FYP/drone_autonomous/PC2/scripts')
from mavlink_lite import DroneConnection, MAVLink

telemetry = {
    "connected": 0, "armed": 0, "mode": 0,
    "alt": 0, "battery": 0, "heading": 0,
    "lat": 0, "lon": 0, "fix_type": 0, "satellites": 0,
    "speed": 0, "roll": 0, "pitch": 0, "yaw": 0,
    "vel_x": 0, "vel_y": 0, "vel_z": 0,
}

# Known obstacle positions in Dodoma world (x, y, z, type, radius)
# These are static obstacles the drone should avoid
OBSTACLES = [
    # Trees (acacia)
    (-40, 25, 0, "tree", 1.8), (40, 25, 0, "tree", 1.8),
    (-40, -25, 0, "tree", 1.8), (40, -25, 0, "tree", 1.8),
    (-150, 100, 0, "tree", 2.2), (150, -100, 0, "tree", 2.2),
    (-30, 40, 0, "tree", 1.7), (30, 40, 0, "tree", 1.6),
    (-30, -40, 0, "tree", 1.9), (30, -40, 0, "tree", 1.5),
    (-60, -50, 0, "tree", 2.0), (60, 50, 0, "tree", 1.8),
    (50, -55, 0, "tree", 1.7), (-50, 55, 0, "tree", 1.9),
    (100, 80, 0, "tree", 2.3), (-100, -80, 0, "tree", 2.0),
    (-100, 50, 0, "baobab", 2.5), (100, -50, 0, "baobab", 2.8),
    # Buildings
    (-20, 20, 0, "building", 6), (20, 20, 0, "building", 7),
    (20, -20, 0, "building", 5), (-30, -25, 0, "building", 10),
    (30, -30, 0, "building", 5), (-45, 20, 0, "building", 3),
    (45, 20, 0, "building", 4), (-45, -20, 0, "building", 4),
    (20, -65, 0, "building", 8), (40, -65, 0, "building", 4.5),
    (5, -65, 0, "building", 4), (80, -40, 0, "parliament", 10),
    (50, 30, 0, "building", 6), (-50, 35, 0, "building", 5),
    (35, 15, 0, "kiosk", 2), (-35, -15, 0, "kiosk", 2),
    (80, 30, 0, "warehouse", 7),
    # Roundabout
    (0, 0, 0, "roundabout", 5.5),
    # Jersey barriers
    (15, 9, 0, "barrier", 0.5), (18, 9, 0, "barrier", 0.5),
    (-15, 9, 0, "barrier", 0.5), (-18, 9, 0, "barrier", 0.5),
    (15, -9, 0, "barrier", 0.5), (18, -9, 0, "barrier", 0.5),
    (-15, -9, 0, "barrier", 0.5), (-18, -9, 0, "barrier", 0.5),
    # Vehicles
    (15, 15, 0, "car", 2), (-15, -15, 0, "car", 2),
    (85, -30, 0, "car", 2), (25, 25, 0, "truck", 2.5),
    (-60, 40, 0, "truck", 2.5), (55, -35, 0, "bus", 2.5),
    (-55, 50, 0, "suv", 2.2), (-30, 45, 0, "motorcycle", 0.6),
    # Cones
    (10, 10, 0, "cone", 0.3), (-10, 10, 0, "cone", 0.3),
    (10, -10, 0, "cone", 0.3), (-10, -10, 0, "cone", 0.3),
    (8, -8, 0, "cone", 0.3), (-8, 8, 0, "cone", 0.3),
    # Construction barriers
    (11, -6, 0, "barrier", 1), (13, -6, 0, "barrier", 1),
    (-11, -6, 0, "barrier", 1), (-13, -6, 0, "barrier", 1),
    # Containers
    (75, -25, 0, "container", 2.5), (75, -22, 0, "container", 2.5),
    # Street furniture
    (55, 12, 0, "shelter", 1.5), (-55, 12, 0, "shelter", 1.5),
    (12, 8, 0, "bin", 0.4), (-12, 8, 0, "bin", 0.4),
    (12, -8, 0, "bin", 0.4), (-12, -8, 0, "bin", 0.4),
    (22, 12, 0, "hydrant", 0.3),
    (70, 10, 0, "billboard", 1.5), (-70, -10, 0, "billboard", 1.5),
    (90, 60, 0, "water_tower", 2),
    # Speed bumps (low obstacles)
    (60, 0, 0, "speedbump", 1.5), (-60, 0, 0, "speedbump", 1.5),
    # Gazebo test structure
    (0, 150, 0, "gazebo", 4.5),
    # Bushes
    (10, 10, 0, "bush", 0.5), (-10, -10, 0, "bush", 0.5),
    (70, 90, 0, "bush", 0.6), (70, -80, 0, "bush", 0.5),
    (-70, 80, 0, "bush", 0.55), (-80, -70, 0, "bush", 0.45),
]

RADAR_HTML = r'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Drone PPI Radar</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:#0b0e14;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:monospace;overflow:hidden}
  #wrapper{position:relative}
  canvas{display:block;background:radial-gradient(circle at center,#0d1117 0%,#05080c 100%);border-radius:50%}
  #info{position:absolute;bottom:15px;left:15px;color:#88ccff;font:12px monospace;text-shadow:0 0 4px #000;pointer-events:none}
  #hdg{position:absolute;top:15px;left:50%;transform:translateX(-50%);color:#ffcc00;font:bold 14px monospace;text-shadow:0 0 6px #ffcc0044;pointer-events:none}
  #status{position:absolute;bottom:15px;right:15px;color:#4a7db5;font:11px monospace;text-shadow:0 0 4px #000;pointer-events:none;text-align:right}
</style>
</head>
<body>
<div id="wrapper">
<canvas id="c" width="800" height="800"></canvas>
<div id="info">Waiting for data...</div>
<div id="hdg">HDG: ---°</div>
<div id="status">CONNECTING...</div>
</div>
<script>
(function(){
var c=document.getElementById('c'),ctx=c.getContext('2d'),W=800,H=800,CX=400,CY=400,MAX=200;
var alt=0,hdg=0,con=0,obs=[],sectors=[0,0,0,0,0,0,0,0,0,0,0,0];
function p2c(r,b){var rr=(r/MAX)*320,br=(b-90)*Math.PI/180;return{x:CX+rr*Math.cos(br),y:CY+rr*Math.sin(br)}}
function draw(){
 ctx.clearRect(0,0,W,H);ctx.fillStyle='#0b0e14';ctx.fillRect(0,0,W,H);
 [50,100,150,200].forEach(function(r){
  var rr=(r/MAX)*320;ctx.beginPath();ctx.arc(CX,CY,rr,0,2*Math.PI);
  ctx.strokeStyle=r==200?'#1a3a5a':'#0f2a44';ctx.lineWidth=r==200?1.5:0.8;ctx.stroke();
  ctx.fillStyle='#3a6a9a';ctx.font='10px monospace';ctx.textAlign='left';ctx.fillText(r+'m',CX+rr+5,CY+4)
 });
 ctx.beginPath();ctx.arc(CX,CY,320,0,2*Math.PI);ctx.strokeStyle='#1a5a8a';ctx.lineWidth=2;ctx.stroke();
 for(var i=0;i<12;i++){
  var a=(i*30-90)*Math.PI/180,x2=CX+320*Math.cos(a),y2=CY+320*Math.sin(a);
  ctx.beginPath();ctx.moveTo(CX,CY);ctx.lineTo(x2,y2);
  ctx.strokeStyle=i%3==0?'#1a3a5a':'#0d1f33';ctx.lineWidth=i%3==0?1:0.5;ctx.stroke();
  var lr=335;ctx.fillStyle='#4a7db5';ctx.font='10px monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(i*30+'\u00b0',CX+lr*Math.cos(a),CY+lr*Math.sin(a))
 }
 var dirs={N:-90,E:0,S:90,W:180};Object.keys(dirs).forEach(function(d){
  var a=dirs[d]*Math.PI/180,lr=355;ctx.fillStyle='#5a8aba';ctx.font='bold 14px monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(d,CX+lr*Math.cos(a),CY+lr*Math.sin(a))
 });
 for(var s=0;s<12;s++){
  var sa=(s*30-90)*Math.PI/180,ea=((s+1)*30-90)*Math.PI/180,c=sectors[s]||0;
  if(c>0){var h=Math.min(120,Math.max(0,120-c*15));ctx.beginPath();ctx.arc(CX,CY,300,sa,ea);ctx.strokeStyle='hsla('+h+',100%,50%,0.6)';ctx.lineWidth=8;ctx.stroke();var ma=(sa+ea)/2;ctx.fillStyle='#66ff66';ctx.font='bold 11px monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(c,CX+305*Math.cos(ma),CY+305*Math.sin(ma))}
 }
 var tc={tree:'#33cc33',baobab:'#339933',building:'#ff6633',parliament:'#ff3333',barrier:'#ffcc00',car:'#66aaff',truck:'#4488cc',bus:'#ffaa00',suv:'#5599dd',motorcycle:'#88ccff',cone:'#ff8800',container:'#aa66cc',shelter:'#66cccc',bin:'#88aa44',hydrant:'#ff4444',billboard:'#cc88ff',water_tower:'#66aaff',speedbump:'#aa8844',gazebo:'#88aacc',bush:'#55aa44',kiosk:'#88aa66',roundabout:'#888888'};
 obs.forEach(function(o){
  var p=p2c(o.range_m,o.bearing_deg),cl=tc[o.type]||'#aaa',br=Math.max(4,Math.min(10,o.radius_m*1.5));
  ctx.beginPath();ctx.arc(p.x,p.y,br+2,0,2*Math.PI);ctx.fillStyle=cl+'44';ctx.fill();
  ctx.beginPath();ctx.arc(p.x,p.y,br,0,2*Math.PI);ctx.fillStyle=cl;ctx.fill();ctx.strokeStyle='#fff8';ctx.lineWidth=.5;ctx.stroke()
 });
 ctx.beginPath();ctx.arc(CX,CY,6,0,2*Math.PI);ctx.fillStyle='#0f0';ctx.fill();ctx.strokeStyle='#0f0a';ctx.lineWidth=1.5;ctx.stroke();
 var hr=(hdg-90)*Math.PI/180;ctx.beginPath();ctx.moveTo(CX,CY);ctx.lineTo(CX+35*Math.cos(hr),CY+35*Math.sin(hr));ctx.strokeStyle='#0f0';ctx.lineWidth=2.5;ctx.stroke();
 ctx.beginPath();ctx.arc(CX,CY,2.5,0,2*Math.PI);ctx.fillStyle='#fff';ctx.fill();
 var el=document.getElementById('info'),sl=document.getElementById('status'),hl=document.getElementById('hdg');
 if(obs.length>0){var n=obs[0];el.innerHTML='Obstacles: '+obs.length+' | Nearest: '+n.type+' @ '+n.range_m+'m / '+n.bearing_deg+'\u00b0 | Alt: '+alt.toFixed(1)+'m'}
 else el.innerHTML='No obstacles within '+MAX+'m | Alt: '+alt.toFixed(1)+'m | '+(con?'ONLINE':'OFFLINE');
 hl.innerHTML='HDG: '+hdg+'\u00b0';sl.innerHTML='Lat: -6.1630'+'\nLon: 35.7516'+'\nAlt: '+alt.toFixed(1)+'m\nBat: ---%\nObs: '+obs.length+'\n'+(con?'CONNECTED':'OFFLINE')
}
function fetch(){
 var x=new XMLHttpRequest();x.open('GET','/obstacles',true);x.timeout=3000;
 x.onload=function(){if(x.status==200){try{var d=JSON.parse(x.responseText);obs=d.obstacles||[];sectors=[0,0,0,0,0,0,0,0,0,0,0,0];obs.forEach(function(o){sectors[Math.floor(o.bearing_deg/30)%12]++});con=1}catch(e){}}};
 x.onerror=function(){con=0};x.send();
 var t=new XMLHttpRequest();t.open('GET','/metrics',true);t.timeout=3000;
 t.onload=function(){if(t.status==200){t.responseText.split('\n').forEach(function(l){if(l.startsWith('drone_altitude_m '))alt=parseFloat(l.split(' ')[1])||0;if(l.startsWith('drone_heading_deg '))hdg=parseFloat(l.split(' ')[1])||0})}};t.send()
}
function ani(){var sa=(Date.now()*.02)%360,rad=(sa-90)*Math.PI/180;draw();ctx.beginPath();ctx.moveTo(CX,CY);ctx.lineTo(CX+320*Math.cos(rad),CY+320*Math.sin(rad));ctx.strokeStyle='#0f04';ctx.lineWidth=1;ctx.stroke();ctx.beginPath();ctx.moveTo(CX,CY);ctx.arc(CX,CY,320,rad-.05,rad);ctx.closePath();ctx.fillStyle='#0f0006';ctx.fill();requestAnimationFrame(ani)}
setInterval(fetch,2000);fetch();ani()
})();
</script>
</body>
</html>'''

def compute_range_bearing(drone_x, drone_y, drone_z, obj_x, obj_y, obj_z):
    dx = obj_x - drone_x
    dy = obj_y - drone_y
    dz = obj_z - drone_z
    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    bearing = math.degrees(math.atan2(dy, dx))
    if bearing < 0:
        bearing += 360
    return dist, bearing

def detect_obstacles(drone_x, drone_y, drone_z, max_range=200):
    detected = []
    for ox, oy, oz, otype, orad in OBSTACLES:
        dist, bearing = compute_range_bearing(drone_x, drone_y, drone_z, ox, oy, oz)
        if dist <= max_range:
            detected.append({
                "type": otype,
                "range_m": round(dist, 1),
                "bearing_deg": round(bearing, 1),
                "radius_m": orad,
            })
    detected.sort(key=lambda o: o["range_m"])
    return detected

def mavlink_loop():
    global telemetry
    mavlink_target = os.getenv('PC2_IP', '127.0.0.1')
    while True:
        try:
            conn = DroneConnection(udp_target=(mavlink_target, 14550))
            conn.connect()
            while True:
                t = conn.get_telemetry()
                telemetry["connected"] = 1 if t["connected"] else 0
                telemetry["armed"] = 1 if t["armed"] else 0
                telemetry["mode"] = {"UNKNOWN":0,"MANUAL":1,"ALTCTL":2,"POSCTL":3,"AUTO":4,"ACRO":5,"OFFBOARD":6,"STABILIZED":7,"RATTITUDE":8,"AUTO.LOITER":9,"AUTO.RTL":10,"AUTO.LAND":11,"AUTO.TAKEOFF":12}.get(t["mode"], 0)
                telemetry["alt"] = t["alt"]
                telemetry["battery"] = t["battery"]
                telemetry["heading"] = t["heading"]
                telemetry["lat"] = t["lat"]
                telemetry["lon"] = t["lon"]
                telemetry["fix_type"] = t["fix_type"]
                telemetry["satellites"] = t["satellites"]
                telemetry["speed"] = t.get("speed", 0)
                time.sleep(1)
        except Exception as e:
            telemetry["connected"] = 0
            time.sleep(3)

threading.Thread(target=mavlink_loop, daemon=True).start()
time.sleep(1)

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            t = telemetry
            lines = [
                '# HELP drone_connected Drone connection status',
                '# TYPE drone_connected gauge',
                f'drone_connected {t["connected"]}',
                '# HELP drone_armed Drone armed status',
                '# TYPE drone_armed gauge',
                f'drone_armed {t["armed"]}',
                '# HELP drone_flight_mode Current flight mode',
                '# TYPE drone_flight_mode gauge',
                f'drone_flight_mode {t["mode"]}',
                '# HELP drone_altitude_m Drone altitude in meters',
                '# TYPE drone_altitude_m gauge',
                f'drone_altitude_m {t["alt"]}',
                '# HELP drone_battery_pct Battery percentage',
                '# TYPE drone_battery_pct gauge',
                f'drone_battery_pct {t["battery"]}',
                '# HELP drone_heading_deg Heading in degrees',
                '# TYPE drone_heading_deg gauge',
                f'drone_heading_deg {t["heading"]}',
                '# HELP drone_latitude GPS latitude',
                '# TYPE drone_latitude gauge',
                f'drone_latitude {t["lat"]}',
                '# HELP drone_longitude GPS longitude',
                '# TYPE drone_longitude gauge',
                f'drone_longitude {t["lon"]}',
                '# HELP drone_gps_fix_type GPS fix type',
                '# TYPE drone_gps_fix_type gauge',
                f'drone_gps_fix_type {t["fix_type"]}',
                '# HELP drone_gps_satellites GPS satellite count',
                '# TYPE drone_gps_satellites gauge',
                f'drone_gps_satellites {t["satellites"]}',
                '# HELP drone_gps GPS coordinates with lat/lon labels',
                '# TYPE drone_gps gauge',
                f'drone_gps{{coord="lat"}} {t["lat"]}',
                f'drone_gps{{coord="lon"}} {t["lon"]}',
                '# HELP drone_battery_pct_clamped Battery percentage (0-100)',
                '# TYPE drone_battery_pct_clamped gauge',
                f'drone_battery_pct_clamped {max(0, min(100, math.floor(t["battery"])))}',
                '# HELP drone_speed_m_s Drone ground speed in m/s',
                '# TYPE drone_speed_m_s gauge',
                f'drone_speed_m_s {t["speed"]}',
            ]

            # Add obstacle detection metrics
            drone_x = 0
            drone_y = 0
            drone_z = t["alt"]
            detected = detect_obstacles(drone_x, drone_y, drone_z, max_range=200)

            lines.append('# HELP drone_obstacle_count Number of detected obstacles in range')
            lines.append('# TYPE drone_obstacle_count gauge')
            lines.append(f'drone_obstacle_count {len(detected)}')

            lines.append('# HELP drone_obstacle_nearest_range_m Range to nearest obstacle (meters)')
            lines.append('# TYPE drone_obstacle_nearest_range_m gauge')
            nearest_range = detected[0]["range_m"] if detected else 999
            lines.append(f'drone_obstacle_nearest_range_m {nearest_range}')

            lines.append('# HELP drone_obstacle_nearest_bearing_deg Bearing to nearest obstacle (degrees)')
            lines.append('# TYPE drone_obstacle_nearest_bearing_deg gauge')
            nearest_bear = detected[0]["bearing_deg"] if detected else 0
            lines.append(f'drone_obstacle_nearest_bearing_deg {nearest_bear}')

            lines.append('# HELP drone_obstacle_nearest_type Type of nearest obstacle')
            lines.append('# TYPE drone_obstacle_nearest_type gauge')
            type_map = {"tree":0,"baobab":1,"building":2,"parliament":3,"barrier":4,"car":5,"truck":6,"bus":7,"suv":8,"motorcycle":9,"cone":10,"container":11,"shelter":12,"bin":13,"hydrant":14,"billboard":15,"water_tower":16,"speedbump":17,"gazebo":18,"bush":19,"kiosk":20,"roundabout":21}
            nearest_type = type_map.get(detected[0]["type"], 99) if detected else 99
            lines.append(f'drone_obstacle_nearest_type {nearest_type}')

            # Per-bearing-sector obstacle counts (for radar sectors)
            lines.append('# HELP drone_obstacles_by_sector Obstacle count per 30-degree sector')
            lines.append('# TYPE drone_obstacles_by_sector gauge')
            for sector in range(12):
                start_b = sector * 30
                end_b = start_b + 30
                count = sum(1 for o in detected if start_b <= o["bearing_deg"] < end_b)
                lines.append(f'drone_obstacles_by_sector{{sector="{sector}",start="{start_b}",end="{end_b}"}} {count}')

            # Raw obstacle distances for radar blips
            lines.append('# HELP drone_obstacle_radar_blip Individual obstacle detections for radar')
            lines.append('# TYPE drone_obstacle_radar_blip gauge')
            for i, obs in enumerate(detected[:30]):
                lines.append(f'drone_obstacle_radar_blip{{id="{i}",type="{obs["type"]}",range="{obs["range_m"]}",bearing="{obs["bearing_deg"]}"}} 1')

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('\n'.join(lines).encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status":"ok","connected":bool(telemetry["connected"])}).encode())
        elif self.path == '/obstacles':
            drone_x = 0
            drone_y = 0
            drone_z = telemetry["alt"]
            detected = detect_obstacles(drone_x, drone_y, drone_z, max_range=200)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"count": len(detected), "obstacles": detected}, indent=2).encode())
        elif self.path == '/radar':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(RADAR_HTML.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

server = HTTPServer(('0.0.0.0', 8007), MetricsHandler)
print("drone_exporter: listening on :8007/metrics, :8007/obstacles, :8007/radar")
server.serve_forever()
