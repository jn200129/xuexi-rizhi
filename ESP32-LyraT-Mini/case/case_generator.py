"""
ESP32-LyraT-Mini 桌面智能音箱 - 横版桌面式外壳参数化建模

设计原则：
- 100×80×40 mm 桌面横版
- 主体 U 型（5 面）+ 顶盖 1 片，4 颗 M2 螺丝固定
- 左侧屏窗口 30×34，右侧 Φ36 喇叭孔（前面板）
- 侧面开孔：右 6 键 · 左 SD 卡 / Micro-USB
- 底部 4 根 PCB 支撑柱 + 4 根到顶的螺柱

坐标系：
  X 左→右  0..100
  Y 前→后  0..80  （Y=0 面板正对用户）
  Z 底→顶  0..40
"""
import os, sys
FCPATH = r"D:\FreeCAD\FreeCAD_1.1.1-Windows-x86_64-py311\bin"
if FCPATH not in sys.path:
    sys.path.insert(0, FCPATH)
import FreeCAD as App
import Part, Mesh, MeshPart
from FreeCAD import Base

# ========= 参数（按需修改后重跑即得新 STL）=========
W, D, H         = 100.0, 80.0, 40.0   # 外形宽/深/高
WALL            = 2.4                  # 侧壁厚
FLOOR           = 2.0                  # 底板厚
LID_THICK       = 2.5                  # 顶盖厚
LID_STEP        = 2.0                  # 顶盖嵌入深度
LID_CLEARANCE   = 0.3                  # 顶盖与主体台阶的间隙

# 屏窗口（前面板 Y=0）
SCR_X, SCR_Z    = 15.0, 4.0            # 左下角
SCR_W, SCR_H    = 30.0, 34.0           # 30×34mm，够 1.9" IPS 显示区留 3mm 边

# 喇叭孔（前面板）
SPK_CX, SPK_CZ  = 72.0, 20.0
SPK_R           = 18.0                 # Ø36 mm，配 40 mm 喇叭

# 6 键 (右侧 X=W)
BTN_R           = 1.75                 # Ø3.5 mm 孔
BTN_Z           = 20.0                 # 一排横向
BTN_YS          = [12, 24, 36, 48, 60, 72]

# SD 卡口 (左侧 X=0)
SD_CY, SD_CZ    = 22.0, 8.0
SD_W, SD_H      = 20.0, 3.0

# Micro-USB (左侧 X=0)
USB_CY, USB_CZ  = 52.0, 8.0
USB_W, USB_H    = 8.0, 4.0

# PCB 支撑柱
PCB_POSTS       = [(18, 25), (82, 25), (18, 55), (82, 55)]
PCB_H           = 12.0
PCB_OD, PCB_ID  = 5.0, 1.7             # M2 自攻

# 顶盖螺柱 (贯穿主体，M2 自攻)
LID_POSTS       = [(6, 6), (W-6, 6), (6, D-6), (W-6, D-6)]
POST_OD, POST_ID = 5.5, 1.7
POST_H          = H - LID_STEP - LID_CLEARANCE   # 到台阶下

# 顶盖沉头
LID_SCREW_HEAD_D, LID_SCREW_HEAD_H = 4.4, 1.5
LID_SCREW_SHAFT_D = 2.3

# 前面板麦克风孔阵列（喇叭上方，用于让麦克风声音进来）
MIC_ARR_CX, MIC_ARR_CZ = 72.0, 36.0
MIC_ARR_ROWS, MIC_ARR_COLS = 1, 5
MIC_ARR_PITCH = 3.0
MIC_R = 0.6

OUT_DIR = r"D:\lyrat_mini_case\output"
os.makedirs(OUT_DIR, exist_ok=True)

# ========= 工具函数 =========
def box(x, y, z, w, d, h):
    return Part.makeBox(w, d, h).translate(Base.Vector(x, y, z))

def cyl_z(cx, cy, z, r, h):
    """圆柱轴 // Z"""
    return Part.makeCylinder(r, h).translate(Base.Vector(cx, cy, z))

def cyl_y(cx, cz, y, r, h):
    """圆柱轴 // Y (从前面板挖孔用)"""
    c = Part.makeCylinder(r, h)
    c.rotate(Base.Vector(0,0,0), Base.Vector(1,0,0), -90)
    return c.translate(Base.Vector(cx, y, cz))

def cyl_x(cy, cz, x, r, h):
    """圆柱轴 // X (从侧面挖孔用)"""
    c = Part.makeCylinder(r, h)
    c.rotate(Base.Vector(0,0,0), Base.Vector(0,1,0), 90)
    return c.translate(Base.Vector(x, cy, cz))

# ========= 主体（U 型 + 底 + 前后左右四面）=========
def build_main():
    print("[主体] 建外壳...")
    outer = box(0, 0, 0, W, D, H)
    inner = box(WALL, WALL, FLOOR, W-2*WALL, D-2*WALL, H-FLOOR)  # 内腔
    body = outer.cut(inner)

    # 顶部开口（把 Z=H-LID_STEP..H 那层内轮廓外延出到外壁 - 保留内台阶）
    print("[主体] 挖顶部开口...")
    lid_open = box(WALL, WALL, H-LID_STEP, W-2*WALL, D-2*WALL, LID_STEP+0.1)
    body = body.cut(lid_open)

    # 挖屏窗口
    print("[主体] 挖屏窗口...")
    body = body.cut(box(SCR_X, -0.1, SCR_Z, SCR_W, WALL+0.2, SCR_H))

    # 挖喇叭圆孔
    print("[主体] 挖喇叭孔...")
    body = body.cut(cyl_y(SPK_CX, SPK_CZ, -0.1, SPK_R, WALL+0.2))

    # 6 键孔
    print("[主体] 挖 6 键...")
    for y in BTN_YS:
        body = body.cut(cyl_x(y, BTN_Z, W-WALL-0.1, BTN_R, WALL+0.2))

    # SD 卡口
    print("[主体] 挖 SD 口...")
    body = body.cut(box(-0.1, SD_CY - SD_W/2, SD_CZ - SD_H/2, WALL+0.2, SD_W, SD_H))

    # Micro-USB 口
    print("[主体] 挖 USB 口...")
    body = body.cut(box(-0.1, USB_CY - USB_W/2, USB_CZ - USB_H/2, WALL+0.2, USB_W, USB_H))

    # 麦克风阵列孔
    print("[主体] 打麦克风孔阵列...")
    for r in range(MIC_ARR_ROWS):
        for c in range(MIC_ARR_COLS):
            cx = MIC_ARR_CX + (c - (MIC_ARR_COLS-1)/2) * MIC_ARR_PITCH
            cz = MIC_ARR_CZ + (r - (MIC_ARR_ROWS-1)/2) * MIC_ARR_PITCH
            body = body.cut(cyl_y(cx, cz, -0.1, MIC_R, WALL+0.2))

    # PCB 支撑柱
    print("[主体] 加 PCB 支撑柱...")
    for cx, cy in PCB_POSTS:
        post = cyl_z(cx, cy, FLOOR, PCB_OD/2, PCB_H)
        hole = cyl_z(cx, cy, FLOOR, PCB_ID/2, PCB_H+0.1)
        post = post.cut(hole)
        body = body.fuse(post)

    # 顶盖螺柱（贯穿高度到台阶下）
    print("[主体] 加顶盖螺柱...")
    for cx, cy in LID_POSTS:
        post = cyl_z(cx, cy, FLOOR, POST_OD/2, POST_H - FLOOR)
        hole = cyl_z(cx, cy, FLOOR, POST_ID/2, POST_H - FLOOR + 0.1)
        post = post.cut(hole)
        body = body.fuse(post)

    return body

# ========= 顶盖 =========
def build_lid():
    print("[顶盖] 建外形...")
    top_outer = box(0, 0, H-LID_THICK, W, D, LID_THICK)
    # 嵌入台阶部分 (内缩)
    step = box(WALL + LID_CLEARANCE, WALL + LID_CLEARANCE,
               H - LID_STEP,
               W - 2*(WALL + LID_CLEARANCE),
               D - 2*(WALL + LID_CLEARANCE),
               LID_STEP - LID_THICK if LID_STEP>LID_THICK else 0.1)
    # 若嵌入台阶更深就并上
    lid = top_outer
    if LID_STEP > LID_THICK:
        lid = lid.fuse(step)

    # 螺丝穿孔 + 沉头
    print("[顶盖] 打 4 沉头孔...")
    for cx, cy in LID_POSTS:
        # 穿孔（全穿）
        shaft = cyl_z(cx, cy, H-LID_STEP-1, LID_SCREW_SHAFT_D/2, LID_STEP+2)
        lid = lid.cut(shaft)
        # 沉头凹（顶面向下）
        head  = cyl_z(cx, cy, H - LID_SCREW_HEAD_H, LID_SCREW_HEAD_D/2, LID_SCREW_HEAD_H+0.1)
        lid = lid.cut(head)

    return lid

# ========= 输出 =========
def export(shape, name):
    step_path = os.path.join(OUT_DIR, f"{name}.step")
    stl_path  = os.path.join(OUT_DIR, f"{name}.stl")
    shape.exportStep(step_path)
    mesh = MeshPart.meshFromShape(shape, LinearDeflection=0.15, AngularDeflection=0.4)
    mesh.write(stl_path)
    print(f"  -> {step_path}")
    print(f"  -> {stl_path}  ({os.path.getsize(stl_path)//1024} KB)")

def main():
    body = build_main()
    lid  = build_lid()
    export(body, "LyraT_case_main")
    export(lid,  "LyraT_case_lid")

    # 装配预览 = 主体 + 顶盖
    print("[装配] 生成 assembly...")
    assembly = body.fuse(lid)
    export(assembly, "LyraT_case_assembly")

    print("=== 完成 ===")

main()
