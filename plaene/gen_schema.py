# -*- coding: utf-8 -*-
# Erzeugt einen Übersichtsplan Sicherheitsbeleuchtung im Stil des Vorlagenplans
# (E30-Unterstation, Leuchtenketten mit SL/RZ, Plotterschrift, grün)

G = "#1f8a1f"      # Plottergrün
BK = "#1a1a1a"     # Schwarz
MONO = "Courier New, Courier, monospace"

rows = [
    ("1a", "1", [("KG/014","SL","1/1"),("KG/022","RZ","1/2"),("KG/024","SL","1/3")]),
    ("1b", "1", [("KG/014","SL","2/1"),("Außen","SL","2/2"),("KG/022","RZ","2/3"),("KG/024","SL","2/4")]),
    ("2a", "2", [("KG/010","SL","3/1"),("KG/023","RZ","3/2"),("KG/024","SL","3/3"),("KG/024","RZ","3/4")]),
    ("2b", "2", [("KG/024","SL","4/1"),("KG/023","SL","4/2"),("KG/024","RZ","4/3"),("KG/024","SL","4/4")]),
    ("3a", "3", [("EG/113","SL","5/1"),("EG/113","RZ","5/2"),("1.OG/214","SL","5/3")]),
    ("3b", "3", [("EG/113","SL","6/1"),("Außen","SL","6/2"),("EG/113","RZ","6/3"),("KG/022","SL","6/4"),("1.OG/214","SL","6/5"),("2.OG/313","SL","6/6")]),
    ("4a", "2", [("EG/114","SL","7/1"),("EG/114","RZ","7/2")]),
    ("4b", "2", [("EG/114","RZ","8/1"),("EG/114","SL","8/2")]),
    ("5a", "4", [("EG/115","SL","9/1"),("EG/115","RZ","9/2"),("EG/116","RZ","9/3"),("EG/116","SL","9/4"),("EG/120","RZ","9/5")]),
    ("5b", "4", [("EG/115","RZ","10/1"),("EG/115","SL","10/2"),("EG/116","RZ","10/3"),("EG/120","SL","10/4")]),
    ("6a", "5", [("EG/121","SL","11/1"),("Außen","SL","11/2"),("KG/029","RZ","11/3"),("EG/121","RZ","11/4"),("1.OG/221","SL","11/5"),("2.OG/322","SL","11/6")]),
    ("6b", "5", [("EG/121","RZ","12/1"),("EG/121","SL","12/2"),("1.OG/222","SL","12/3"),("2.OG/322","SL","12/4")]),
]

W, H = 1600, 1100
Y0, DY = 118, 70              # erste Zeile, Zeilenabstand
TX1, TX2, TX3 = 130, 200, 262 # Tabelle: links, Spaltentrenner, rechts
X0, DX = 336, 138             # erstes Symbol, Symbolabstand

s = []
s.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="{MONO}" fill="{BK}">')
s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fdfdf8"/>')
s.append(f'<rect x="25" y="25" width="{W-50}" height="{H-50}" fill="none" stroke="{BK}" stroke-width="2"/>')
s.append(f'<rect x="33" y="33" width="{W-66}" height="{H-66}" fill="none" stroke="{BK}" stroke-width="0.8"/>')

def txt(x, y, t, size=11, fill=BK, anchor="middle", weight="normal", extra=""):
    t = (t.replace("&","&amp;").replace("<","&lt;"))
    s.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" {extra}>{t}</text>')

def leuchte(cx, cy):
    # X-Kreuz mit gefülltem "Doppeldreieck" (Bowtie) – wie Vorlage
    s.append(f'<g stroke="{G}" stroke-width="1.6">')
    s.append(f'<line x1="{cx-13}" y1="{cy-13}" x2="{cx+13}" y2="{cy+13}"/>')
    s.append(f'<line x1="{cx-13}" y1="{cy+13}" x2="{cx+13}" y2="{cy-13}"/>')
    s.append('</g>')
    s.append(f'<polygon points="{cx-12},{cy-8} {cx-1},{cy} {cx-12},{cy+8}" fill="{G}"/>')
    s.append(f'<polygon points="{cx+12},{cy-8} {cx+1},{cy} {cx+12},{cy+8}" fill="{G}"/>')

# ---------------- Unterstation-Tabelle ----------------
tab_top, tab_bot = Y0 - 40, Y0 + (len(rows)-1)*DY + 34
s.append(f'<rect x="{TX1}" y="{tab_top}" width="{TX3-TX1}" height="{tab_bot-tab_top}" fill="none" stroke="{BK}" stroke-width="1.4"/>')
s.append(f'<line x1="{TX2}" y1="{tab_top}" x2="{TX2}" y2="{tab_bot}" stroke="{BK}" stroke-width="0.9"/>')
s.append(f'<line x1="{TX1}" y1="{tab_top+28}" x2="{TX3}" y2="{tab_bot-(tab_bot-tab_top-28)}" stroke="{BK}" stroke-width="0.9"/>')
txt((TX1+TX2)/2, tab_top+13, "Baugr.-", 9.5); txt((TX1+TX2)/2, tab_top+24, "Nr.", 9.5)
txt((TX2+TX3)/2, tab_top+13, "DSL/3Ph", 9.5); txt((TX2+TX3)/2, tab_top+24, "-Nr.", 9.5)
txt(105, (tab_top+tab_bot)/2, "E30 Unterstation", 15, BK, "middle", "bold",
    f'transform="rotate(-90 105 {(tab_top+tab_bot)/2})" letter-spacing="3"')

for i, (baugr, dsl, chain) in enumerate(rows):
    y = Y0 + i*DY
    txt((TX1+TX2)/2, y+4, baugr, 12)
    txt((TX2+TX3)/2, y+4, dsl, 12)
    if i:  # Zeilentrenner
        s.append(f'<line x1="{TX1}" y1="{y-DY/2+4}" x2="{TX3}" y2="{y-DY/2+4}" stroke="{BK}" stroke-width="0.6"/>')
    # Kette
    prev = TX3
    for j, (raum, typ, nr) in enumerate(chain):
        cx = X0 + j*DX
        s.append(f'<line x1="{prev}" y1="{y}" x2="{cx-14}" y2="{y}" stroke="{G}" stroke-width="1.3"/>')
        leuchte(cx, y)
        txt(cx, y-32, raum, 10.5, G)
        txt(cx, y-18, typ, 11, G, "middle", "bold")
        txt(cx, y+24, nr, 10.5, G)
        prev = cx + 14

txt(X0, Y0 + (len(rows)-1)*DY + 50, "weitere Stromkreise 13/1 … 20/5 (1. OG / 2. OG) analog", 11, G, "start")

# ---------------- Einspeisung ----------------
mid = (TX1+TX3)/2
s.append(f'<line x1="{mid}" y1="{tab_bot}" x2="{mid}" y2="{tab_bot+26}" stroke="{BK}" stroke-width="1.6"/>')
s.append(f'<polygon points="{mid-5},{tab_bot+10} {mid+5},{tab_bot+10} {mid},{tab_bot}" fill="{BK}"/>')
feed = ["Einspeisung 5 x 25 qmm von Zentralbatterie",
        "Einbau von externen DLS/3Ph-Bus-Modul in folgende Verteilungen:",
        "UV 1.1, 1.2 / UV 2.1, 2.2 / UV 3.1, 3.2",
        "Verdrahtung der Bus-Module mit IY(ST)Y 2x2x0,8"]
for k, line in enumerate(feed):
    txt(60, 962 + k*18, line, 12, BK, "start")

# ---------------- Legende (grün) ----------------
lx, ly = 1170, 120
leg = ["B  Bereitschaftslicht", "D  Dauerlicht", "DL geschaltetes Dauerlicht", "",
       "Alle RZ-Leuchten in Dauerlicht", "",
       "Alle nicht gekennzeichneten", "Sicherheitsleuchten in", "geschaltetem Dauerlicht",
       "über EIB in Verbindung", "mit DLS-Modul."]
for k, line in enumerate(leg):
    txt(lx, ly+k*19, line, 12.5, G, "start")

# ---------------- Schriftfeld ----------------
bx, by, bw, bh = 880, 860, 687, 207   # bis Innenrahmen (33..1567 / ..1067)
bx2, by2 = bx+bw, by+bh
s.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="#ffffff" stroke="{BK}" stroke-width="1.6"/>')
# Index/Änderungs-Leiste
s.append(f'<line x1="{bx}" y1="{by+26}" x2="{bx2}" y2="{by+26}" stroke="{BK}" stroke-width="1"/>')
for xv, t in [(bx+30,"Index"),(bx+150,"Änderung"),(bx+330,"Name"),(bx+430,"Datum")]:
    txt(xv, by+17, t, 10, BK, "start")
s.append(f'<line x1="{bx+90}" y1="{by}" x2="{bx+90}" y2="{by+26}" stroke="{BK}" stroke-width="0.7"/>')
s.append(f'<line x1="{bx+310}" y1="{by}" x2="{bx+310}" y2="{by+26}" stroke="{BK}" stroke-width="0.7"/>')
s.append(f'<line x1="{bx+410}" y1="{by}" x2="{bx+410}" y2="{by+26}" stroke="{BK}" stroke-width="0.7"/>')
# Firma (rechts oben)
s.append(f'<line x1="{bx+500}" y1="{by}" x2="{bx+500}" y2="{by+80}" stroke="{BK}" stroke-width="1"/>')
txt(bx+505, by+42, "«Elektrofirma»", 12, BK, "start", "bold")
txt(bx+505, by+58, "Meisterbetrieb", 10, BK, "start")
txt(bx+505, by+72, "«Straße · PLZ Ort · Tel.»", 9.5, BK, "start")
# Bauherr / Objekt
s.append(f'<line x1="{bx}" y1="{by+80}" x2="{bx2}" y2="{by+80}" stroke="{BK}" stroke-width="1"/>')
txt(bx+8, by+40, "Bauherr:", 10, BK, "start")
txt(bx+8, by+58, "«Bauherr / Auftraggeber»", 12, BK, "start", "bold")
txt(bx+8, by+95, "Objekt:", 10, BK, "start")
txt(bx+8, by+113, "«Bauvorhaben, Straße, Ort»", 12, BK, "start", "bold")
s.append(f'<line x1="{bx}" y1="{by+124}" x2="{bx2}" y2="{by+124}" stroke="{BK}" stroke-width="1"/>')
# Darstellung
txt(bx+8, by+139, "Darstellung:", 10, BK, "start")
txt(bx+8, by+157, "Übersichtsplan Elektrotechnik", 13, BK, "start", "bold")
txt(bx+8, by+175, "Sicherheitsbeleuchtung – E30-Unterstation", 12, BK, "start")
s.append(f'<line x1="{bx+380}" y1="{by+124}" x2="{bx+380}" y2="{by2}" stroke="{BK}" stroke-width="1"/>')
# rechte Felder
txt(bx+388, by+139, "Projekt-Id.-Nr.: «0000-00.0»", 10.5, BK, "start")
txt(bx+388, by+157, "Maßstab: o. M.", 10.5, BK, "start")
txt(bx+388, by+175, "Bl.-Nr.: 006A", 10.5, BK, "start")
s.append(f'<line x1="{bx}" y1="{by+185}" x2="{bx2}" y2="{by+185}" stroke="{BK}" stroke-width="1"/>')
txt(bx+8, by+201, "Zeichnungs-Nr.: «731.00 – 01 – A – EL – 8 – 006A / 03»", 10.5, BK, "start")
txt(bx+388, by+201, "Planer/Datum: «Name» / 05.07.2026", 10.5, BK, "start")

s.append('</svg>')

out = "/tmp/claude-0/-home-user-twyne-contracts-v1/61ab2837-1b2e-59a3-8813-3e6cf07b00ce/scratchpad/uebersichtsplan-e30-unterstation.svg"
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(s))
print(out)
