# Membuat flow.json (jalankan: python build_flow.py)
import json
KEY = "iot-kampus-123"
CORS = "msg.headers = {'Access-Control-Allow-Origin': '*'};\n"
def auth(two=False):
    ret = "[msg, null]" if two else "msg"
    return (CORS + "if ((msg.req.headers['x-api-key'] || '') !== '%s') {\n"
            "  msg.statusCode = 401;\n  msg.payload = {status:'error', message:'API key salah atau tidak ada'};\n"
            "  return %s;\n}\n") % (KEY, ret)

N = []
def fn(id, name, code, outs, wires, x, y):
    N.append({"id":id,"type":"function","z":"flow_api","name":name,"func":code,"outputs":outs,
              "noerr":0,"initialize":"","finalize":"","libs":[],"x":x,"y":y,"wires":wires})
def hin(id, name, url, method, wire, y):
    N.append({"id":id,"type":"http in","z":"flow_api","name":name,"url":url,"method":method,
              "upload":False,"swaggerDoc":"","x":170,"y":y,"wires":[[wire]]})
def hres(id, x, y):
    N.append({"id":id,"type":"http response","z":"flow_api","name":"","statusCode":"","headers":{},"x":x,"y":y,"wires":[]})

N.append({"id":"flow_api","type":"tab","label":"IoT REST API","disabled":False,"info":""})
N.append({"id":"mqtt_broker_config","type":"mqtt-broker","name":"Local Mosquitto","broker":"localhost",
          "port":"1883","clientid":"node-red-backend","autoConnect":True,"usetls":False,"protocolVersion":"4",
          "keepalive":"60","cleansession":True})
N.append({"id":"mqtt_sensor_in","type":"mqtt in","z":"flow_api","name":"Subscribe Sensor","topic":"iot/sensor",
          "qos":"0","datatype":"json","broker":"mqtt_broker_config","x":170,"y":60,"wires":[["store_sensor"]]})
fn("store_sensor","Simpan Data + Cek Batas", """var d = msg.payload;
d.received = new Date().toISOString();
flow.set('lastSensor', d);
var h = flow.get('history') || [];
h.push(d); if (h.length > 50) h.shift();
flow.set('history', h);

// BONUS 1: cek threshold -> notifikasi
var th = flow.get('threshold');
if (th !== undefined && d.suhu > th) {
  var alert = {alert:true, message:'Suhu ' + d.suhu + ' C melewati batas ' + th + ' C', time:d.received};
  flow.set('alert', alert);
  return [msg, {topic:'iot/alert', payload:alert}];
}
flow.set('alert', null);
return [msg, null];""", 2, [["debug_sensor"],["mqtt_alert","debug_sensor"]], 410, 60)
N.append({"id":"debug_sensor","type":"debug","z":"flow_api","name":"Log","active":True,"tosidebar":True,
          "console":False,"tostatus":False,"complete":"payload","targetType":"msg","x":650,"y":60,"wires":[]})
N.append({"id":"mqtt_alert","type":"mqtt out","z":"flow_api","name":"Publish Alert","topic":"","qos":"0",
          "retain":"false","broker":"mqtt_broker_config","x":650,"y":110,"wires":[]})

hin("h1","GET /api/suhu","/api/suhu","get","f1",190)
fn("f1","Build Response Suhu", auth() + """var data = flow.get('lastSensor') || {suhu:null, kelembaban:null, timestamp:null};
msg.statusCode = 200;
msg.payload = {status:'success', data:data, threshold:flow.get('threshold') ?? null,
               alert:flow.get('alert') || null, server_time:new Date().toISOString()};
return msg;""",1,[["r1"]],410,190); hres("r1",640,190)

hin("h2","GET /api/history","/api/history","get","f2",270)
fn("f2","Build Response History", auth() + """var h = flow.get('history') || [];
msg.statusCode = 200;
msg.payload = {status:'success', count:h.length, data:h};
return msg;""",1,[["r2"]],410,270); hres("r2",640,270)

hin("h3","POST /api/kontrol","/api/kontrol","post","f3",350)
fn("f3","Validasi & Publish", auth(True) + """var b = msg.payload || {};
if (!b.device || !b.action) {
  msg.statusCode = 400;
  msg.payload = {status:'error', message:'device dan action wajib diisi'};
  return [msg, null];
}
var out = {topic:'iot/kontrol', payload:b};
msg.statusCode = 200;
msg.payload = {status:'success', message:'Perintah terkirim', sent:b};
return [msg, out];""",2,[["r3"],["mqtt_kontrol"]],410,350); hres("r3",640,330)
N.append({"id":"mqtt_kontrol","type":"mqtt out","z":"flow_api","name":"Publish Kontrol","topic":"","qos":"0",
          "retain":"false","broker":"mqtt_broker_config","x":650,"y":380,"wires":[]})

hin("h4","PUT /api/threshold","/api/threshold","put","f4",450)
fn("f4","Set Threshold", auth() + """var v = Number(msg.payload && msg.payload.suhu_max);
if (isNaN(v)) {
  msg.statusCode = 400;
  msg.payload = {status:'error', message:'suhu_max harus angka'};
  return msg;
}
flow.set('threshold', v);
msg.statusCode = 200;
msg.payload = {status:'success', message:'Batas suhu diset', threshold:v};
return msg;""",1,[["r4"]],410,450); hres("r4",640,450)

for i, p in enumerate(["suhu","history","kontrol","threshold"]):
    hin("h5_"+p, "OPTIONS /api/"+p, "/api/"+p, "options", "f5", 530 + i*50)
fn("f5","CORS Headers","""msg.statusCode = 204;
msg.payload = '';
msg.headers = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, X-API-Key'
};
return msg;""",1,[["r5"]],410,530); hres("r5",640,530)
json.dump(N, open("flow.json","w"), indent=2, ensure_ascii=False)
print("flow.json dibuat,", len(N), "node")
