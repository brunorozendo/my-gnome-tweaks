import math
# macOS curve for HIDMouseAcceleration=45056 (0.6875), from this Mac's HIDAccelCurves; algorithm from IOHIDFamily
GL,GP,GC,T0,T1=0.94,0.71,0.12,8.4,17.0
y0=GL*T0+(GP*T0)**2+(GC*T0)**3
m0=GL+2*T0*GP**2+3*T0**2*GC**3
b0=y0-m0*T0
y1=m0*T1+b0
m1=2*y1*m0
b1=y1**2-m1*T1
def mac_y(v):
    if v<=T0: return GL*v+(GP*v)**2+(GC*v)**3
    if v<=T1: return m0*v+b0
    return math.sqrt(m1*v+b1)
def mac(c,hz,res=400,rate=67):
    per_report=max(1,math.floor(c/hz))
    v=per_report/(res/rate)
    return mac_y(v)*(96/67)/per_report
# libinput 1.31.3 src/filter-mouse.c, linear profile; speed_in in 1000dpi-units/ms
def li(c,s,dpi=1000):
    x=(c/dpi)
    th=max(0.4-0.25*s,0.2); cap=2+1.5*s; inc=1.1+0.75*s
    if x<0.07: f=10*x+0.3
    elif x<th: f=1
    else: f=inc*(x-th)+1
    return min(cap,f)*1000/dpi
cs=[100,200,400,800,1500,3000,5000]
grid=[int(100*(60**(i/40))) for i in range(41)]
def err(fn,hz):
    return math.sqrt(sum(math.log(fn(c)/mac(c,hz))**2 for c in grid)/len(grid))
for name,hz in (("ELECOM 125Hz",125),("Dell receiver 500Hz",500)):
    print(f"\n{name}: px/count at counts/sec {cs}")
    print(" macOS        ",[round(mac(c,hz),2) for c in cs])
    for s in (0,-0.5,-0.7,-0.8,-0.9,-1):
        print(f" gnome {s:>5}  ",[round(li(c,s),2) for c in cs]," rms %.0f%%"%((math.exp(err(lambda c:li(c,s),hz))-1)*100))
    best=min(((err(lambda c:li(c,s/100),hz),s/100) for s in range(-100,101)))
    print(" best gsettings-only:",best[1],"rms %.0f%%"%((math.exp(best[0])-1)*100))
    b=min(((err(lambda c:li(c,s/20,d),hz),d,s/20) for d in range(1000,6001,100) for s in range(-20,21)))
    print(f" best with MOUSE_DPI override: dpi={b[1]} speed={b[2]} rms {(math.exp(b[0])-1)*100:.0f}%")
    print("   ",[round(li(c,b[2],b[1]),2) for c in cs])

print("\n--- common GNOME speed, per-mouse MOUSE_DPI")
res=[]
for s20 in range(-20,21):
    s=s20/20
    e1,d1=min((err(lambda c:li(c,s,d),125),d) for d in range(1000,6001,100))
    e2,d2=min((err(lambda c:li(c,s,d),500),d) for d in range(1000,6001,100))
    res.append((max(e1,e2),s,d1,e1,d2,e2))
for r in sorted(res)[:4]:
    print(f"speed={r[1]} ELECOM dpi={r[2]} rms {(math.exp(r[3])-1)*100:.0f}% | Dell dpi={r[4]} rms {(math.exp(r[5])-1)*100:.0f}%")
b=sorted(res)[0]
print(" ELECOM",[round(li(c,b[1],b[2]),2) for c in cs]," mac",[round(mac(c,125),2) for c in cs])
print(" Dell  ",[round(li(c,b[1],b[4]),2) for c in cs]," mac",[round(mac(c,500),2) for c in cs])
