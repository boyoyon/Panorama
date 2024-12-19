import cv2, os, sys
import glfw
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

#画像幅をALIGNピクセルの倍数にcropする
ALIGN = 4

# マウスドラッグ中かどうか
isDragging = False

# マウスのクリック位置
oldPos = [0, 0]
newPos = [0, 0]

# 操作の種類
MODE_NONE = 0x00
MODE_TRANSLATE = 0x01
MODE_ROTATE = 0x02
MODE_SCALE = 0x04


# マウス移動量と回転、平行移動の倍率
ROTATE_SCALE = 10.0
TRANSLATE_SCALE = 500.0

# 座標変換のための変数
Mode = MODE_NONE
Scale = 5.0

MODEL_SIZE = 1.0

# スキャンコード定義
SCANCODE_LEFT  = 331
SCANCODE_RIGHT = 333
SCANCODE_UP    = 328
SCANCODE_DOWN  = 336

# キーコード定義
KEY_R = 82
KEY_S = 83
KEY_H = 72
KEY_V = 86
KEY_I = 73
KEY_Z = 90

KEY_STATE_NONE = 0
KEY_STATE_PRESS_H = 1
KEY_STATE_PRESS_V = 2
KEY_STATE_PRESS_CTRL = 4

KeyState = KEY_STATE_NONE
PrevKeyState = KEY_STATE_NONE

# 方位角、仰角
AZIMUTH = 0.0
ELEVATION = 0.0
ROLL = 0.0

dAZIMUTH = 0.0
dELEVATION = 0.0

MODS_SHIFT = 1

# モデル位置
ModelPos = [0.0, 0.0]

# テクスチャー画像
textureImage = None

WIN_WIDTH = 600  # ウィンドウの幅 / Window width
WIN_HEIGHT = 800  # ウィンドウの高さ / Window height
WIN_TITLE = "Panorama"  # ウィンドウのタイトル / Window title

TEX_FILE = None
textureId = 0

idxModel = None

frameNo = 1

NR_DIVS = 45 

points = np.empty((NR_DIVS+1, NR_DIVS+1, 3), np.float32)
texcoords = np.empty((NR_DIVS+1, NR_DIVS+1, 2), np.float32)

#AngleHorz = np.pi * 2 / 5
#AngleVert = np.pi / 5
AngleHorz = np.pi * 2
AngleVert = np.pi

fInertia = False

def createSphere(size):

    global points, texcoords

    x0 = 0.0
    y0 = size
    z0 = 0.0
    
    startAlpha = (np.pi - AngleVert) / 2
    startBeta = (np.pi * 2 - AngleHorz) / 2

    for i in range(NR_DIVS+1):


        alpha = i * AngleVert / NR_DIVS + startAlpha

        x1 = x0
        y1 = np.cos(alpha) * y0 - np.sin(alpha) * z0
        z1 = np.sin(alpha) * y0 + np.cos(alpha) * z0

        ty = i / NR_DIVS

        for j in range(NR_DIVS+1):

            beta = j * AngleHorz / NR_DIVS + startBeta

            z2 = np.cos(beta) * x1 - np.sin(beta) * z1
            x2 = np.sin(beta) * x1 + np.cos(beta) * z1
            y2 = y1

            points[i][j] = (x2, y2, z2)

            tx = j / NR_DIVS
            texcoords[i][j] = (tx, ty)

def createFace():

    glBegin(GL_TRIANGLES)

    for i in range(NR_DIVS):

        for j in range(NR_DIVS):
           
            # Triangle 1

            glTexCoord2fv(texcoords[i][j])
            glNormal3fv(points[i][j])
            glVertex3fv(points[i][j])
        
            glTexCoord2fv(texcoords[i+1][j+1])
            glNormal3fv(points[i+1][j+1])
            glVertex3fv(points[i+1][j+1])
        
            glTexCoord2fv(texcoords[i+1][j])
            glNormal3fv(points[i+1][j])
            glVertex3fv(points[i+1][j])
    
            # Triangle 2

            glTexCoord2fv(texcoords[i][j])
            glNormal3fv(points[i][j])
            glVertex3fv(points[i][j])
        
            glTexCoord2fv(texcoords[i][j+1])
            glNormal3fv(points[i][j+1])
            glVertex3fv(points[i][j+1])
        
            glTexCoord2fv(texcoords[i+1][j+1])
            glNormal3fv(points[i+1][j+1])
            glVertex3fv(points[i+1][j+1])
        
    glEnd()

# OpenGLの初期化関数
def initializeGL():
    global textureId, idxModel

    # 背景色の設定 (黒)
    glClearColor(0.0, 0.0, 0.0, 1.0)

    # 深度テストの有効化
    glEnable(GL_DEPTH_TEST)

    # 後面削除
    glEnable(GL_CULL_FACE)

    # テクスチャの有効化
    glEnable(GL_TEXTURE_2D)

    # テクスチャの設定

    image = textureImage

    texHeight, texWidth, _ = image.shape

    # テクスチャの生成と有効化
    textureId = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, textureId)

    gluBuild2DMipmaps(GL_TEXTURE_2D, GL_RGB8, texWidth, texHeight, GL_RGB, GL_UNSIGNED_BYTE, image.tobytes())

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)

    # テクスチャ境界の折り返し設定
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    # テクスチャの無効化
    glBindTexture(GL_TEXTURE_2D, 0)

    createSphere(MODEL_SIZE)

    idxModel = glGenLists(1)
    glNewList(idxModel, GL_COMPILE)
    createFace()
    glEndList()

# OpenGLの描画関数
def paintGL():

    if WIN_HEIGHT > 0:

        global PrevKeyState, idxModel
    
        # 背景色と深度値のクリア
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
        # 投影変換行列
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        #gluPerspective(10.0, WIN_WIDTH / WIN_HEIGHT, 1.0, 100.0)
        gluPerspective(45.0, WIN_WIDTH / WIN_HEIGHT, 1.0, 100.0)
    
    
        # モデルビュー行列
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        gluLookAt(0.0, 0.0, -5.0,   # 視点の位置
            0.0, 0.0, 0.0,   # 見ている先
            0.0, -1.0, 0.0)  # 視界の上方向
      
        #gluLookAt(0.0, 0.0, 0.0,   # 視点の位置
        #    0.0, 0.0, -1.0,   # 見ている先
        #    0.0, -1.0, 0.0)  # 視界の上方向
    
        # 平面の描画
        glBindTexture(GL_TEXTURE_2D, textureId)  # テクスチャの有効化
    
        # 水平画角、垂直画角の調整が終わったらディスプレイリストをコンパイル
        if KeyState != PrevKeyState and KeyState == KEY_STATE_NONE:
    
            createSphere(MODEL_SIZE)
            glDeleteLists(idxModel, 1)
            idxModel = glGenLists(1)
            glNewList(idxModel, GL_COMPILE)
            createFace()
            glEndList()
    
        PrevKeyState = KeyState
    
        glPushMatrix()
        glScalef(Scale, Scale, Scale)
        glTranslatef(ModelPos[0], ModelPos[1], 0.0)
        glRotatef(ELEVATION, 1.0, 0.0, 0.0)
        glRotatef(AZIMUTH, 0.0, 1.0, 0.0)
        glRotatef(ROLL, 0.0, 0.0, 1.0)
    
        # 水平画角、垂直画角調整中はディスプレイリストを使わず描画
        # いちいちコンパイルすると却って遅くなるため 
        if KeyState == KEY_STATE_PRESS_H or KeyState == KEY_STATE_PRESS_V:
    
            createSphere(MODEL_SIZE)
            createFace()
    
        else:
            glCallList(idxModel)
    
        glPopMatrix()
    
        glBindTexture(GL_TEXTURE_2D, 0)  # テクスチャの無効化


# ウィンドウサイズ変更のコールバック関数
def resizeGL(window, width, height):
    global WIN_WIDTH, WIN_HEIGHT

    # ユーザ管理のウィンドウサイズを変更
    WIN_WIDTH = width
    WIN_HEIGHT = height

    # GLFW管理のウィンドウサイズを変更
    glfw.set_window_size(window, WIN_WIDTH, WIN_HEIGHT)

    # 実際のウィンドウサイズ (ピクセル数) を取得
    renderBufferWidth, renderBufferHeight = glfw.get_framebuffer_size(window)

    # ビューポート変換の更新
    glViewport(0, 0, renderBufferWidth, renderBufferHeight)

# アニメーションのためのアップデート
def animate():
    global AZIMUTH, ELEVATION

    # 慣性モード中は回転し続ける
    if fInertia and not isDragging:
        AZIMUTH -= dAZIMUTH
        ELEVATION += dELEVATION

def save_screen():
    global frameNo

    width = WIN_WIDTH
    height = WIN_HEIGHT

    glReadBuffer(GL_FRONT)
    screen_shot = np.zeros((height, width, 3), np.uint8)
    glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE, screen_shot.data)
    screen_shot = cv2.cvtColor(screen_shot, cv2.COLOR_RGB2BGR)
    screen_shot = cv2.flip(screen_shot, 0)
    filename = 'screenshot_%04d.png' % frameNo
    cv2.imwrite(filename, screen_shot)
    print('saved %s' % filename)
    frameNo += 1

# キーボードの押し離しを扱うコールバック関数
def keyboardEvent(window, key, scancode, action, mods):
    global AZIMUTH, ELEVATION, dAZIMUTH, dELEVATION, KeyState, idxModel, fInertia, Scale

    # 矢印キー操作

    if scancode == SCANCODE_LEFT:
        dAZIMUTH = -0.1
        AZIMUTH -= dAZIMUTH * 10

    if scancode == SCANCODE_RIGHT:
        dAZIMUTH = 0.1
        AZIMUTH -= dAZIMUTH * 10

    if scancode == SCANCODE_DOWN:
        dELEVATION = 0.1
        ELEVATION += dELEVATION * 10

    if scancode == SCANCODE_UP:
        dELEVATION = -0.1
        ELEVATION += dELEVATION * 10
    
    if key == KEY_Z:
        if mods == MODS_SHIFT:
            Scale += 0.1
        else:
            Scale -= 0.1

    # sキー押下でスクリーンショット
    if key == KEY_S and action == 1: # press, releaseで2回キャプチャーしないように
        save_screen()

    # ホィールモードの選択

    if key == KEY_R:
        if action == glfw.PRESS:
            KeyState = KEY_STATE_PRESS_CTRL
        elif action == 0:
            KeyState = KEY_STATE_NONE

    if key == KEY_H:
        if action == glfw.PRESS:
            KeyState = KEY_STATE_PRESS_H
        elif action == 0:
            KeyState = KEY_STATE_NONE

    if key == KEY_V:
        if action == glfw.PRESS:
            KeyState = KEY_STATE_PRESS_V
        elif action == 0:
            KeyState = KEY_STATE_NONE

    # 慣性モードのトグル

    if key == KEY_I and action == 1:
        fInertia = not fInertia

# マウスのクリックを処理するコールバック関数
def mouseEvent(window, button, action, mods):
    global isDragging, newPos, oldPos, Mode, fInertia

    # クリックしたボタンで処理を切り替える
    if button == glfw.MOUSE_BUTTON_LEFT:
        Mode = MODE_ROTATE
    
    elif button == glfw.MOUSE_BUTTON_MIDDLE:
        if action == 1:
            fInertia = not fInertia

    elif button == glfw.MOUSE_BUTTON_RIGHT:
        Mode = MODE_TRANSLATE

    # クリックされた位置を取得
    px, py = glfw.get_cursor_pos(window)

    # マウスドラッグの状態を更新
    if action == glfw.PRESS:
        if not isDragging:
            isDragging = True
            oldPos = [px, py]
            newPos = [px, py]
    else:
        isDragging = False
        oldPos = [0, 0]
        newPos = [0, 0]

# マウスの動きを処理するコールバック関数
def motionEvent(window, xpos, ypos):
    global isDragging, newPos, oldPos, AZIMUTH, dAZIMUTH, ELEVATION, dELEVATION, ModelPos

    if isDragging:
        # マウスの現在位置を更新
        newPos = [xpos, ypos]

        dx = newPos[0] - oldPos[0]
        dy = newPos[1] - oldPos[1]
        
        # マウスがあまり動いていない時は処理をしない
        #length = dx * dx + dy * dy
        #if length < 2.0 * 2.0:
        #    return
        #else:
        if Mode == MODE_ROTATE:
            dAZIMUTH = (xpos - oldPos[0]) / ROTATE_SCALE
            dELEVATION = (ypos - oldPos[1]) / ROTATE_SCALE
            AZIMUTH -= dAZIMUTH
            ELEVATION += dELEVATION
        elif Mode == MODE_TRANSLATE:
            ModelPos[0] += (xpos - oldPos[0]) / TRANSLATE_SCALE
            ModelPos[1] += (ypos - oldPos[1]) / TRANSLATE_SCALE

        oldPos = [xpos, ypos]

# マウスホイールを処理するコールバック関数
def wheelEvent(window, xoffset, yoffset):
    global Scale, AngleHorz, AngleVert, idxModel, ROLL

    if KeyState == KEY_STATE_NONE:
        Scale += yoffset / 10.0

    elif KeyState == KEY_STATE_PRESS_CTRL:
        ROLL += yoffset

    elif KeyState == KEY_STATE_PRESS_H:
        AngleHorz += yoffset / 10.0
        if AngleHorz > np.pi * 2:
            AngleHorz = np.pi * 2
        if AngleHorz < np.pi * 2 / NR_DIVS:
            AngleHorz = NR_DIVS

    elif KeyState == KEY_STATE_PRESS_V:
        AngleVert += yoffset / 10.0
        if AngleVert > np.pi:
            AngleVert = np.pi
        if AngleVert < np.pi / NR_DIVS:
            AngleVert = np.pi / NR_DIVS

# 画像の横幅がALIGNピクセルの倍数になるようにクロップする
# そうしないとうまくテクスチャーマッピングされないため
def prescale(image):
    height, width = image.shape[:2]

    if width % ALIGN != 0:
        WIDTH = width // ALIGN * ALIGN
        startX = (width - WIDTH) // 2
        endX = startX + WIDTH

        dst = np.empty((height, WIDTH, 3), np.uint8)
        dst = image[:, startX:endX]
        return dst

    else:
        return image

def main():

    global TEX_FILE, textureImage

    argv = sys.argv
    argc = len(argv)

    if argc < 2:
        print('%s maps image on to a sphere' % argv[0])
        print('%s <image>' % argv[0])
        quit()

    TEX_FILE = argv[1]

    img = cv2.imread(TEX_FILE, cv2.IMREAD_COLOR)
    img = prescale(img)
    img = cv2.flip(img, 0)
    textureImage = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # OpenGLを初期化する
    if glfw.init() == glfw.FALSE:
        raise Exception("Failed to initialize OpenGL")

    # Windowの作成
    window = glfw.create_window(WIN_WIDTH, WIN_HEIGHT, WIN_TITLE, None, None)
    if window is None:
        glfw.terminate()
        raise Exception("Failed to create Window")

    # OpenGLの描画対象にWindowを追加
    glfw.make_context_current(window)

    # ウィンドウのリサイズを扱う関数の登録
    glfw.set_window_size_callback(window, resizeGL)

    # キーボードのイベントを処理する関数を登録
    glfw.set_key_callback(window, keyboardEvent)

    # マウスのイベントを処理する関数を登録
    glfw.set_mouse_button_callback(window, mouseEvent)

    # マウスの動きを処理する関数を登録
    glfw.set_cursor_pos_callback(window, motionEvent)

    # マウスホイールを処理する関数を登録
    glfw.set_scroll_callback(window, wheelEvent)
    
    # ユーザ指定の初期化
    initializeGL()

    # メインループ
    while glfw.window_should_close(window) == glfw.FALSE:
        # 描画
        paintGL()

        # アニメーション
        animate()

        # 描画用バッファの切り替え
        glfw.swap_buffers(window)
        glfw.poll_events()

    # 後処理
    glfw.destroy_window(window)
    glfw.terminate()


if __name__ == "__main__":
    main()
