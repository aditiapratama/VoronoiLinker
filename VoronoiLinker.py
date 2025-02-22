# ! License agreements are not described. Code style conventions are not respected. Naming conventions are not respected.
# ! Соглашения об лицензиях не описаны. Соглашения о стиле кода не соблюдены. Соглашения об наименованиях не соблюдены.

#This addon is a self-writing for me personally, which I made publicly available to everyone wishing. Because this addon is awesome.
#Этот аддон является самописом лично для меня, который я сделал публичным для всех желающих. Ибо результат получился потрясающий.

#Отдаю свою идею этого аддона, и его самого в руки общественного достояния. Делайте с этим что хотите.

#Так же надеюсь, что вы простите мне использование только одного файла. 1) Это удобно, всего один файл. 2) До версии 3.5 NodeWrangler так же поставлялся одним файлом.

bl_info = {'name':"Voronoi Linker", 'author':"ugorek", 'version':(2,4,3), 'blender':(3,5,1), #2023.07.01
           'description':"Various utilities for nodes connecting, based on the distance field", 'location':"Node Editor > Alt + RMB", 'warning':"", 'category':"Node",
           'wiki_url':"https://github.com/ugorek000/VoronoiLinker/wiki", 'tracker_url':"https://github.com/ugorek000/VoronoiLinker/issues"}

from builtins import len as length #Невозможность использования "мобильной" 3-х буквенной переменной с именем "len" -- проклятье воплати.
#Мой первый язык -- Delphi. Python -- второй. В Delphi имеется "Length();". От чего я надеюсь вы простите мне мою дерзость, но я буду пользоваться этим.
import bpy, blf, gpu, gpu_extras.batch
#С модулем gpu_extras чёрная магия какая-то творится. Просто так его импортировать, чтобы использовать "gpu_extras.batch.batch_for_shader()" -- не работает.
#А с импортом "batch'а" использование "batch.batch_for_shader()" -- тоже не работает. Неведомые мне нано-технологии. Мои знания Python'а слишком малы.
from math import pi, inf, sin, cos, copysign
from mathutils import Vector
#Я не использую "from bpy.props import BoolProperty, и т.д." по своим личным эстетическим причинам. Не забывайте, что это CC0, который изначально создавался лично для меня, и под меня.
#import rna_keymap_ui #Только для вкладки настроек "Keymap".
#import os            #Только для проверки корректного файла шрифта.

voronoiAnchorName = "Voronoi_Anchor"
voronoiSkPreviewName = "voronoi_preview"
voronoiPreviewResultNdName = "SavePreviewResult"

class GlobalVariableParody: #Мои знания Python'а слишком малы.
    gpuLine: gpu.types.GPUShader = None
    gpuArea: gpu.types.GPUShader = None
    fontId = 0
    uiScale = 1.0
    whereActivated = None #CallBack'и рисуются во всех редакторах. Но в тех, у кого нет целевого сокета -- выдаёт ошибку и тем самым ничего не рисуется.
    lastCrutchCollapseNdOut = None
    lastCrutchCollapseNdIn = None
    newKeyMapNodeEditor = None
class MixerGlobalVariable: #То же самое, как и выше, только оформленный под инструмент. Мои знания питона всё ещё слишком малы.
    sk0 = None
    sk1 = None
    skType = None
    list_displayItems = []
    isDisplayVec = False
    displayDeep = 0

globalVars = GlobalVariableParody()
mixerGlbVars = MixerGlobalVariable()


def SetFont(): #Постоянная установка шрифта нужна чтобы шрифт не исчезал при смене темы оформления.
    globalVars.fontId = blf.load(Prefs().dsFontFile)
def UiScale():
    return bpy.context.preferences.system.dpi/72
def GetOpKey(txt):
    return bpy.context.window_manager.keyconfigs.user.keymaps['Node Editor'].keymap_items[txt].type
def PowerArr4ToVec(arr, pw):
    return Vector( (arr[0]**pw, arr[1]**pw, arr[2]**pw, arr[3]**pw))
def GetSkCol(sk):  #Про NodeSocketUndefined см. |2|. Сокеты от потерянных деревьев не имеют "draw_color()".
    return sk.draw_color(bpy.context, sk.node) if sk.bl_idname!='NodeSocketUndefined' else (1.0, 0.2, 0.2, 1.0)
def GetSkColPowVec(sk, pw):
    return PowerArr4ToVec(GetSkCol(sk), pw)
def GetUniformColVec():
    return PowerArr4ToVec(Prefs().dsUniformColor, 1/2.2)
def SkBetweenCheck(txt):
    return txt in ('VALUE', 'RGBA', 'VECTOR', 'INT', 'BOOLEAN')
def RecrGetNodeFinalLoc(nd):
    return nd.location+RecrGetNodeFinalLoc(nd.parent) if nd.parent else nd.location
def VecWorldToRegScale(vec):
    vec = vec.copy()*globalVars.uiScale
    return Vector( bpy.context.region.view2d.view_to_region(vec.x, vec.y, clip=False) )

def DrawWay(vpos, vcol, wid):
    gpu.state.blend_set('ALPHA') #Рисование текста сбрасывает метку об альфе, поэтому устанавливается каждый раз.
    globalVars.gpuLine.bind()
    globalVars.gpuLine.uniform_float('lineWidth', wid)
    gpu_extras.batch.batch_for_shader(globalVars.gpuLine, 'LINE_STRIP', {'pos':vpos, 'color':vcol}).draw(globalVars.gpuLine)
def DrawAreaFan(vpos, col):
    gpu.state.blend_set('ALPHA')
    globalVars.gpuArea.bind()
    globalVars.gpuArea.uniform_float('color', col)
    gpu_extras.batch.batch_for_shader(globalVars.gpuArea, 'TRI_FAN', {'pos':vpos}).draw(globalVars.gpuArea)
def PrepareShaders():
    globalVars.gpuLine = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
    globalVars.gpuArea = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    #Параметры, которые не нужно устанавливать каждый раз:
    globalVars.gpuLine.uniform_float('viewportSize', gpu.state.viewport_get()[2:4])
    #TODO: выяснить как или сделать сглаживание для полигонов тоже.
    globalVars.gpuLine.uniform_float('lineSmooth', True) #Нет нужды, по умолчанию True. Но для экспериментов оставлю.

def DrawLine(pos1, pos2, siz=1, col1=(1.0, 1.0, 1.0, .75), col2=(1.0, 1.0, 1.0, .75)):
    DrawWay((pos1,pos2), (col1,col2), siz)
def DrawStick(pos1, pos2, col1, col2):
    DrawLine(VecWorldToRegScale(pos1), VecWorldToRegScale(pos2), Prefs().dsLineWidth, col1, col2)
def DrawRing(pos, rd, siz=1, col=(1.0, 1.0, 1.0, .75), rotation=0.0, resolution=16):
    vpos = [];  vcol = []
    for cyc in range(resolution+1):
        vpos.append( (rd*cos(cyc*2*pi/resolution+rotation)+pos[0], rd*sin(cyc*2*pi/resolution+rotation)+pos[1]) )
        vcol.append(col)
    DrawWay(vpos, vcol, siz)
def DrawCircle(pos, rd, col=(1.0, 1.0, 1.0, .75), resolution=54):
    #Первая вершина гордо в центре круга, остальные по кругу. Нужно было чтобы артефакты сглаживания были красивыми в центр, а не наклонёнными в куда-то бок.
    vpos = ( (pos[0],pos[1]), *( (rd*cos(i*2.0*pi/resolution)+pos[0], rd*sin(i*2.0*pi/resolution)+pos[1]) for i in range(resolution+1) ) )
    DrawAreaFan(vpos, col)
def DrawRectangle(pos1, pos2, col):
    DrawAreaFan(( (pos1[0],pos1[1]), (pos2[0],pos1[1]), (pos2[0],pos2[1]), (pos1[0],pos2[1]) ), col)

def DrawSocketArea(sk, boxHeiBou, colfac=Vector( (1.0, 1.0, 1.0, 1.0) )):
    loc = RecrGetNodeFinalLoc(sk.node)
    pos1 = VecWorldToRegScale( Vector((loc.x, boxHeiBou[0])) )
    pos2 = VecWorldToRegScale( Vector((loc.x+sk.node.width, boxHeiBou[1])) )
    colfac = colfac if Prefs().dsIsColoredSkArea else Vector(GetUniformColVec())
    DrawRectangle(pos1, pos2, Vector( (1.0, 1.0, 1.0, .075) )*colfac)
def DrawIsLinkedMarker(loc, ofs, skCol):
    ofs[0] += ( (20*Prefs().dsIsDrawSkText+Prefs().dsDistFromCursor)*1.5+Prefs().dsFrameOffset )*copysign(1,ofs[0])+4
    vec = VecWorldToRegScale(loc)
    skCol = skCol if Prefs().dsIsColoredMarker else GetUniformColVec()
    grayCol = 0.65
    col1 = (0.0, 0.0, 0.0, 0.5) #Тень
    col2 = (grayCol, grayCol, grayCol, max(max(skCol[0],skCol[1]),skCol[2])*.9/2) #Прозрачная белая обводка
    col3 = (skCol[0], skCol[1], skCol[2], .925) #Цветная основа
    def DrawMarkerBacklight(tgl, res=16):
        rot = pi/res if tgl else 0.0
        DrawRing( (vec[0]+ofs[0],     vec[1]+5.0+ofs[1]), 9.0, 3, col2, rot, res )
        DrawRing( (vec[0]+ofs[0]-5.0, vec[1]-3.5+ofs[1]), 9.0, 3, col2, rot, res )
    DrawRing( (vec[0]+ofs[0]+1.5, vec[1]+3.5+ofs[1]), 9.0, 3, col1)
    DrawRing( (vec[0]+ofs[0]-3.5, vec[1]-5.0+ofs[1]), 9.0, 3, col1)
    DrawMarkerBacklight(True) #Маркер рисуется с артефактами "дырявых пикселей". Закостылить их дублированной отрисовкой с вращением.
    DrawMarkerBacklight(False) #Но из-за этого нужно уменьшить альфу белой обводки в два раза.
    DrawRing( (vec[0]+ofs[0],     vec[1]+5.0+ofs[1]), 9.0, 1, col3)
    DrawRing( (vec[0]+ofs[0]-5.0, vec[1]-3.5+ofs[1]), 9.0, 1, col3)

def DrawWidePoint(loc, colfac=Vector( (1.0, 1.0, 1.0, 1.0) ), resolution=54, forciblyCol=False): #"forciblyCol" нужен только для DrawDebug'а.
    #Подготовка:
    pos = VecWorldToRegScale(loc)
    loc = Vector( (loc.x+6*Prefs().dsPointRadius*1000, loc.y) ) #Радиус точки вычисляется через мировое пространство. Единственный из двух, кто зависит от зума в редакторе. Второй -- коробка-подсветка сокетов.
    #Умножается и делится на 1000, чтобы радиус не прилипал к целым числам и тем самым был красивее. Конвертация в экранное пространство даёт только целочисленный результат.
    rd = (VecWorldToRegScale(loc)[0]-pos[0])/1000
    #Рисование:
    col1 = Vector( (0.5, 0.5, 0.5, 0.4) )
    col2 = col1
    col3 = Vector( (1.0, 1.0, 1.0, 1.0) )
    colfac = colfac if (Prefs().dsIsColoredPoint)or(forciblyCol) else Vector(GetUniformColVec())
    rd = (rd*rd+10)**0.5
    DrawCircle(pos, rd+3.0, col1*colfac, resolution)
    DrawCircle(pos, rd,     col2*colfac, resolution)
    DrawCircle(pos, rd/1.5, col3*colfac, resolution)

def DrawText(pos, ofs, txt, drawCol, fontSizeOverwrite=0):
    if Prefs().dsIsAllowTextShadow:
        blf.enable(globalVars.fontId, blf.SHADOW)
        muv = Prefs().dsShadowCol
        blf.shadow(globalVars.fontId, (0, 3, 5)[Prefs().dsShadowBlur], muv[0], muv[1], muv[2], muv[3])
        muv = Prefs().dsShadowOffset
        blf.shadow_offset(globalVars.fontId, muv[0], muv[1])
    else: #Большую часть времени бесполезно, но нужно использовать, когда опция рисования тени переключается.
        blf.disable(globalVars.fontId, blf.SHADOW)
    frameOffset = Prefs().dsFrameOffset
    blf.size(globalVars.fontId, Prefs().dsFontSize*(not fontSizeOverwrite)+fontSizeOverwrite)
    #От "текста по факту" не вычисляется, потому что тогда каждая рамка каждый раз будет разной высоты в зависимости от текста.
    #Спецсимвол нужен, как общий случай чтобы покрыть максимальную высоту. Остальные символы нужны для особых шрифтов, что могут быть выше чем █.
    #Но этого недостаточно, некоторые буквы некоторых шрифтов могут вылезти за рамку. Это не чинится, ибо изначально всё было вылизано и отшлифовано для Consolas.
    #И если починить это для всех шрифтов, то тогда рамка для Consolas'а потеряет красоту.
    #P.s. Consolas -- мой самый любимый шрифт после Comic Sans.
    #Если вы хотите тру центрирование -- сделайте это сами.
    txtDim = (blf.dimensions(globalVars.fontId, txt)[0], blf.dimensions(globalVars.fontId, "█GJKLPgjklp!?")[1])
    pos = VecWorldToRegScale(pos)
    pos = ( pos[0]-(txtDim[0]+frameOffset+10)*(ofs[0]<0)+(frameOffset+1)*(ofs[0]>-1), pos[1]+frameOffset )
    pw = 1/1.975 #Осветлить текст. Почему 1.975 -- не помню.
    placePosY = round( (txtDim[1]+frameOffset*2)*ofs[1] ) #Без округления красивость горизонтальных линий пропадет.
    pos1 = (pos[0]+ofs[0]-frameOffset,              pos[1]+placePosY-frameOffset)
    pos2 = (pos[0]+ofs[0]+10+txtDim[0]+frameOffset, pos[1]+placePosY+txtDim[1]+frameOffset)
    gradientResolution = 12
    girderHeight = 1/gradientResolution*(txtDim[1]+frameOffset*2)
    #Рамка для текста
    if Prefs().dsDisplayStyle=='CLASSIC': #Красивая рамка
        #Прозрачный фон:
        def Fx(x, a, b): return ((x+b)/(b+1))**.6*(1-a)+a
        for cyc in range(gradientResolution):
            DrawRectangle( (pos1[0], pos1[1]+cyc*girderHeight), (pos2[0], pos1[1]+cyc*girderHeight+girderHeight), (drawCol[0]/2, drawCol[1]/2, drawCol[2]/2, Fx(cyc/gradientResolution,.2,.05)) )
        #Яркая основная обводка:
        col = (drawCol[0]**pw, drawCol[1]**pw, drawCol[2]**pw, 1.0)
        DrawLine(       pos1,        (pos2[0],pos1[1]), 1, col, col)
        DrawLine( (pos2[0],pos1[1]),        pos2,       1, col, col)
        DrawLine(       pos2,        (pos1[0],pos2[1]), 1, col, col)
        DrawLine( (pos1[0],pos2[1]),        pos1,       1, col, col)
        #Мягкая дополнительная обвода, придающая красоты:
        col = (col[0], col[1], col[2], .375)
        lineOffset = 2.0
        DrawLine( (pos1[0], pos1[1]-lineOffset), (pos2[0], pos1[1]-lineOffset), 1, col, col )
        DrawLine( (pos2[0]+lineOffset, pos1[1]), (pos2[0]+lineOffset, pos2[1]), 1, col, col )
        DrawLine( (pos2[0], pos2[1]+lineOffset), (pos1[0], pos2[1]+lineOffset), 1, col, col )
        DrawLine( (pos1[0]-lineOffset, pos2[1]), (pos1[0]-lineOffset, pos1[1]), 1, col, col )
        #Уголки. Их маленький размер -- маскировка под тру-скругление:
        DrawLine( (pos1[0]-lineOffset, pos1[1]), (pos1[0], pos1[1]-lineOffset), 1, col, col )
        DrawLine( (pos2[0]+lineOffset, pos1[1]), (pos2[0], pos1[1]-lineOffset), 1, col, col )
        DrawLine( (pos2[0]+lineOffset, pos2[1]), (pos2[0], pos2[1]+lineOffset), 1, col, col )
        DrawLine( (pos1[0]-lineOffset, pos2[1]), (pos1[0], pos2[1]+lineOffset), 1, col, col )
    elif Prefs().dsDisplayStyle=='SIMPLIFIED': #Упрощённая рамка. Создана в честь нытиков с гипертрофированным чувством дизайнерской эстетики, я вас не понимаю.
        DrawRectangle( (pos1[0], pos1[1]), (pos2[0], pos2[1]), (drawCol[0]/2.4, drawCol[1]/2.4, drawCol[2]/2.4, .8) )
        col = (.1, .1, .1, .95)
        DrawLine(       pos1,        (pos2[0],pos1[1]), 2, col, col)
        DrawLine( (pos2[0],pos1[1]),        pos2,       2, col, col)
        DrawLine(       pos2,        (pos1[0],pos2[1]), 2, col, col)
        DrawLine( (pos1[0],pos2[1]),        pos1,       2, col, col)
    #Сам текст:
    blf.position(globalVars.fontId, pos[0]+ofs[0]+3.5, pos[1]+placePosY+txtDim[1]*.3, 0)
    blf.color(   globalVars.fontId, drawCol[0]**pw, drawCol[1]**pw, drawCol[2]**pw, 1.0)
    blf.draw(    globalVars.fontId, txt)
    return (txtDim[0]+frameOffset, txtDim[1]+frameOffset*2)
def DrawSkText(pos, ofs, fgSk, fontSizeOverwrite=0):
    if not Prefs().dsIsDrawSkText:
        return [1, 0] #"1" нужен для сохранения информации для направления для позиции маркеров
    skCol = GetSkCol(fgSk.tg) if Prefs().dsIsColoredSkText else GetUniformColVec()
    txt = fgSk.name if fgSk.tg.bl_idname!='NodeSocketVirtual' else bpy.app.translations.pgettext_iface('Virtual')
    return DrawText(pos, ofs, txt, skCol, fontSizeOverwrite)

#Классы ниже созданы для замены списка и повышения читабельности.
class FoundTarget:
    def __init__(self, tg=None, dist=0.0, pos=Vector((0.0, 0.0)), boxHeiBou=[0.0, 0.0], txt=''):
        self.tg = tg
        self.dist = dist
        self.pos = pos
        #Далее нужно только для сокетов
        self.boxHeiBou = boxHeiBou
        self.name = txt #Нужен для поддержки перевода на другие языки. Получать перевод каждый раз при рисовании слишком не комильфо, поэтому вычисляется в заранее.
def GetNearestNodes(nodes, callPos): #Выдаёт список ближайших нод. Честное поле расстояний. Спасибо RayMarching'у, без него я бы до такого не допёр.
    #Почти честное. Скруглённые уголки не высчитываются. Их отсутствие не мешает, вычисление требует много телодвижений. Так что выпендриваться нет нужды.
    list_listNds = []
    for nd in nodes:
        ndLocation = RecrGetNodeFinalLoc(nd) #Расчехлить иерархию родителей и получить итоговую позицию нода.
        #Технический размер рероута явно перезаписан в 4 раза меньше, чем он есть.
        #Насколько я смог выяснить, рероут в отличие от остальных нодов свои размеры при изменении UiScale() не меняет. Так что ему не нужно делиться на "/UiScale()"
        ndSize = Vector( (4,4) ) if nd.bl_idname=='NodeReroute' else nd.dimensions/UiScale()
        #Для нода позицию в центр нода. Позиция рероута уже в центре визуального рероута.
        ndLocation = ndLocation if nd.bl_idname=='NodeReroute' else ndLocation+ndSize/2*Vector( (1,-1) )
        #Сконструировать поле расстояний (Все field'ы - vec2):
        field0 = callPos-ndLocation
        field1 = Vector( ((field0.x>0)*2-1, (field0.y>0)*2-1) )
        field0 = Vector( (abs(field0.x), abs(field0.y)) )-ndSize/2
        field2 = Vector( (max(field0.x, 0), max(field0.y, 0)) )
        field3 = Vector( (abs(field0.x), abs(field0.y)) )
        field3 = field3*Vector( (field3.x<=field3.y, field3.x>field3.y) )
        field3 = field3*-( (field2.x+field2.y)==0 )
        field4 = (field2+field3)*field1
        #Добавить в список отработанный нод
        list_listNds.append( FoundTarget(nd, field4.length, callPos-field4) )
    list_listNds.sort(key=lambda a: a.dist)
    return list_listNds
def GetFromIoPuts(nd, side, callPos):
    list_result = []
    #Так же расшифровать иерархию родителей, как и в поиске ближайшего нода, потому что теперь ищутся сокеты
    ndLocation = RecrGetNodeFinalLoc(nd)
    #"nd.dimensions" уже содержат в себе корректировку на масштаб интерфейса, поэтому вернуть его обратно в мир делением
    ndDim = Vector(nd.dimensions/UiScale())
    #Установить "каретку" в первый сокет своей стороны. Верхний если выход, нижний если вход
    skLocCarriage = Vector( (ndLocation.x+ndDim.x, ndLocation.y-35) ) if side==1 else Vector( (ndLocation.x, ndLocation.y-ndDim.y+16) )
    for sk in nd.outputs if side==1 else reversed(nd.inputs):
        #Игнорировать выключенные и спрятанные
        if (sk.enabled)and(not sk.hide):
            muv = 0 #Для высоты варпа от векторов-сокетов-не-в-одну-строчку.
            #Если текущий сокет -- входящий вектор, и он же свободный и не спрятан в одну строчку
            if (side==-1)and(sk.type=='VECTOR')and(not sk.is_linked)and(not sk.hide_value):
                #Ручками вычисляем занимаемую высоту сокета. Да да. Api на позицию сокета?. Размечтались.
                #Для сферы направления у ShaderNodeNormal и таких же у групп
                if str(sk.bl_rna).find("VectorDirection")!=-1:
                    skLocCarriage.y += 20*2
                    muv = 2
                #И для особо-отличившихся нод с векторами, которые могут быть в одну строчку. Существует всего два нода, у которых к сокету применён ".compact()"
                #Создать такое через api никак, но доступа к этому через api тоже нет. Поэтому обрабатываем по именам явным образом
                elif ( not(nd.type in ('BSDF_PRINCIPLED','SUBSURFACE_SCATTERING')) )or( not(sk.name in ("Subsurface Radius","Radius"))):
                    skLocCarriage.y += 30*2
                    muv = 3
            goalPos = skLocCarriage.copy()
            #Высота Box-Socket-Area так же учитывает текущую высоту мульти-инпута подсчётом количества соединений, но только для входов
            list_result.append(FoundTarget( sk,
                                            (callPos-skLocCarriage).length,
                                            goalPos,
                                            (goalPos.y-11-muv*20, goalPos.y+11+max(length(sk.links)-2,0)*5*(side==-1)),
                                            bpy.app.translations.pgettext_iface(sk.name) ))
            #Сдвинуть до следующего на своё направление
            fix = bpy.context.preferences.view.ui_scale
            fix = -sin(pi*fix)**2 #Что-то тут не число. Замаскировал кривым костылём. У меня нет идей.
            skLocCarriage.y -= 22*side-fix*1.35
    return list_result
def GetNearestSockets(nd, callPos): #Выдаёт список "ближайших сокетов". Честное поле расстояний ячейками Вороного. Да, да, аддон назван именно из-за этого.
    list_fgSksIn = []
    list_fgSksOut = []
    #Обработать ситуацию, когда искать не у кого
    if not nd:
        return list_fgSksIn, list_fgSksOut
    #Если рероут, то имеем простой вариант, не требующий вычисления; вход и выход всего одни, позиции сокетов -- он сам
    if nd.bl_idname=='NodeReroute':
        ndLocation = RecrGetNodeFinalLoc(nd)
        len = Vector(callPos-ndLocation).length
        list_fgSksIn.append( FoundTarget( nd.inputs[0],  len, ndLocation, (-1,-1), bpy.app.translations.pgettext_iface(nd.inputs[0].name ) ))
        list_fgSksOut.append(FoundTarget( nd.outputs[0], len, ndLocation, (-1,-1), bpy.app.translations.pgettext_iface(nd.outputs[0].name) ))
        return list_fgSksIn, list_fgSksOut
    list_fgSksIn =  GetFromIoPuts(nd, -1, callPos)
    list_fgSksOut = GetFromIoPuts(nd, 1,  callPos)
    list_fgSksIn.sort(key=lambda a: a.dist)
    list_fgSksOut.sort(key=lambda a: a.dist)
    return list_fgSksIn, list_fgSksOut

def MinFromFgs(fgSk1, fgSk2):
    if (fgSk2)or(fgSk1): #Если хотя бы один из них существует.
        if not fgSk2: #Если одного из них не существует,
            return fgSk1
        elif not fgSk1: # то остаётся однозначный выбор для второго.
            return fgSk2
        else: #Иначе выбрать ближайшего.
            return fgSk2 if fgSk2.dist<fgSk1.dist else fgSk1
    return None

def DrawDoubleNone(self, context):
    cusorPos = context.space_data.cursor_location
    col = Vector( (1, 1, 1, 1) ) if Prefs().dsIsColoredPoint else GetUniformColVec()
    vec = Vector( (Prefs().dsPointOffsetX*.75, 0) )
    if (Prefs().dsIsDrawLine)and(Prefs().dsIsAlwaysLine):
        DrawStick( cusorPos-vec, cusorPos+vec, col, col )
    if Prefs().dsIsDrawPoint:
        DrawWidePoint(cusorPos-vec, col)
        DrawWidePoint(cusorPos+vec, col)
def EditTreeIsNoneDrawCallback(self, context): #Именно. Ибо эстетика. Вдруг пользователь потеряется; нужно подать признаки жизни.
    if StartDrawCallbackStencil(self, context):
        return
    if Prefs().dsIsDrawPoint:
        cusorPos = context.space_data.cursor_location
        if getattr(self, 'isTwo', False):
            DrawDoubleNone(self, context)
        else:
            DrawWidePoint(cusorPos)
def DrawDebug(self, context):
    def DebugTextDraw(pos, txt, r, g, b):
        blf.size(0,18);  blf.position(0, pos[0]+10,pos[1], 0);  blf.color(0, r,g,b,1.0);  blf.draw(0, txt)
    cusorPos = context.space_data.cursor_location
    DebugTextDraw(VecWorldToRegScale(cusorPos), "Cursor position here.", 1, 1, 1)
    if not context.space_data.edit_tree:
        return
    list_nodes = GetNearestNodes(context.space_data.edit_tree.nodes, cusorPos)
    col = Vector((1, .5, .5, 1))
    DrawStick( cusorPos, list_nodes[0].pos, col, col )
    sco = 0
    for li in list_nodes:
        DrawWidePoint(li.pos, col, 4, True)
        DebugTextDraw( VecWorldToRegScale(li.pos), str(sco)+" Node goal here", col.x, col.y, col.z )
        sco += 1
    list_fgSksIn, list_fgSksOut = GetNearestSockets(list_nodes[0].tg, cusorPos)
    if list_fgSksIn:
        DrawWidePoint( list_fgSksIn[0].pos, Vector((.5, 1, .5, 1)), 4, True )
        DebugTextDraw( VecWorldToRegScale(list_fgSksIn[0].pos), "Nearest socketIn here", .5, 1, .5)
    if list_fgSksOut:
        DrawWidePoint( list_fgSksOut[0].pos, Vector((.5, .5, 1, 1)), 4, True )
        DebugTextDraw( VecWorldToRegScale(list_fgSksOut[0].pos), "Nearest socketOut here", .75, .75, 1)

#Высокоуровневый шаблон рисования для сокетов; тут весь аддон про сокеты, поэтому в названии нет "Sk".
#Пользоваться этим шаблоном невероятно кайфово, после того хардкора что был в предыдущих версиях (даже не заглядывайте туда, там около-ад).
def DrawToolOftenStencil(cusorPos, list_twoTgSks, #Одинаковое со всех инструментов вынесено в этот шаблон.
                         isLineToCursor=False,
                         textSideFlip=False,
                         isDrawText=True,
                         isDrawMarkersMoreTharOne=False,
                         isDrawOnlyArea=False):
    def GetVecOffsetFromSk(sk, y=0.0):
        return Vector( (Prefs().dsPointOffsetX*((sk.is_output)*2-1), y) )
    #Вся суета ради линии:
    if (Prefs().dsIsDrawLine)and(not isDrawOnlyArea):
        len = length(list_twoTgSks)
        if Prefs().dsIsColoredLine:
            col1 = GetSkCol(list_twoTgSks[0].tg)
            col2 = Vector( (1, 1, 1, 1) ) if Prefs().dsIsColoredPoint else GetUniformColVec()
            col2 = col2 if (isLineToCursor)or(len==1) else GetSkCol(list_twoTgSks[1].tg)
        else:
            col1 = GetUniformColVec()
            col2 = col1
        if len>1: #Ниже могут нарисоваться две палки одновременно. Эта ситуация вручную обрабатывается в вызывающей функции на стек выше.
            DrawStick( list_twoTgSks[0].pos+GetVecOffsetFromSk(list_twoTgSks[0].tg), list_twoTgSks[1].pos+GetVecOffsetFromSk(list_twoTgSks[1].tg), col1, col2 )
        if isLineToCursor:
            DrawStick( list_twoTgSks[0].pos+GetVecOffsetFromSk(list_twoTgSks[0].tg), cusorPos, col1, col2 )
    #Всё остальное:
    for li in list_twoTgSks:
        if Prefs().dsIsDrawSkArea:
            DrawSocketArea( li.tg, li.boxHeiBou, GetSkColPowVec(li.tg, 1/2.2) )
        if (Prefs().dsIsDrawPoint)and(not isDrawOnlyArea):
            DrawWidePoint( li.pos+GetVecOffsetFromSk(li.tg), GetSkColPowVec(li.tg, 1/2.2) )
    if isDrawText:
        for li in list_twoTgSks:
            side = (textSideFlip*2-1)
            txtDim = DrawSkText( cusorPos, (Prefs().dsDistFromCursor*(li.tg.is_output*2-1)*side, -.5), li )
            #В условии ".links", но не ".is_linked", потому что линки могут быть выключены (замьючены, красные).
            if (Prefs().dsIsDrawMarker)and( (li.tg.links)and(not isDrawMarkersMoreTharOne)or(length(li.tg.links)>1) ):
                DrawIsLinkedMarker( cusorPos, [txtDim[0]*(li.tg.is_output*2-1)*side, 0], GetSkCol(li.tg) )


def StartDrawCallbackStencil(self, context):
    if globalVars.whereActivated!=context.space_data:
        return True #Нужно чтобы отображалось только в активном редакторе, а не во всех, у кого открыто то же самое дерево.
    PrepareShaders()
    if Prefs().dsIsDrawDebug:
        DrawDebug(self, context)
def ToolInvokeStencilPrepare(self, context, f):
    globalVars.uiScale = UiScale()
    globalVars.whereActivated = context.space_data
    SetFont()
    context.area.tag_redraw()
    self.handle = bpy.types.SpaceNodeEditor.draw_handler_add(f, (self,context), 'WINDOW', 'POST_PIXEL')
    context.window_manager.modal_handler_add(self)


class VoronoiOpBase:
    @classmethod
    def poll(cls, context):
        return context.area.type=='NODE_EDITOR'

def CrutchWithCollapseNode(nd, who, isFinal=False): #Спасибо пользователю с ником "碳酸铷" за идею хоть какой-то обработки свёрнутых нодов. Это должно облегчить симптомы у любителей сворачивать всё.
    if not Prefs().vlAllowCrutchWithCollapsedNode:
        return
    att = getattr(globalVars,'lastCrutchCollapseNd'+who)
    if att:
        if globalVars.lastCrutchCollapseNdIn==globalVars.lastCrutchCollapseNdOut:
            globalVars.lastCrutchCollapseNdIn = None
            return
        att.hide = True
    if (nd)and(nd.hide):
        setattr(globalVars,'lastCrutchCollapseNd'+who, nd)
    if isFinal:
        setattr(globalVars,'lastCrutchCollapseNd'+who, None)
    if nd:
        nd.hide = False
def VoronoiLinkerDrawCallback(self, context):
    if StartDrawCallbackStencil(self, context):
        return
    cusorPos = context.space_data.cursor_location
    if not self.foundGoalSkOut:
        DrawDoubleNone(self, context)
    elif (self.foundGoalSkOut)and(not self.foundGoalSkIn):
        DrawToolOftenStencil( cusorPos, [self.foundGoalSkOut], isLineToCursor=Prefs().dsIsAlwaysLine )
        if Prefs().dsIsDrawPoint: #Точка под курсором шаблоном не обрабатывается.
            DrawWidePoint(cusorPos)
    else:
        DrawToolOftenStencil( cusorPos, [self.foundGoalSkOut, self.foundGoalSkIn] )
class VoronoiLinker(bpy.types.Operator, VoronoiOpBase): # =VL=
    bl_idname = 'node.voronoi_linker'
    bl_label = "Voronoi Linker"
    bl_options = {'UNDO'}
    def NextAssessment(self, context, isBoth):
        #В случае ненайденного подходящего предыдущий выбор остаётся, отчего нельзя вернуть курсор обратно и "отменить" выбор, что очень неудобно.
        self.foundGoalSkIn = None #Поэтому обнуляется каждый раз перед поиском.
        callPos = context.space_data.cursor_location
        for li in GetNearestNodes(context.space_data.edit_tree.nodes, callPos):
            nd = li.tg
            if nd.type=='FRAME': #Рамки пропускаются по очевидным причинам.
                continue
            #Обработать костыль-возможность-использования-свёрнутых-нодов:
            CrutchWithCollapseNode(nd, 'In')
            if isBoth:
                globalVars.lastCrutchCollapseNdOut = globalVars.lastCrutchCollapseNdIn
            #"nd.hide" должно быть использовано после обработки костыля. По очевидным причинам.
            if (nd.hide)and(nd.type!='REROUTE'): #Свёрнутость для рероутов работает, хоть и не отображается визуально.
                continue
            list_fgSksIn, list_fgSksOut = GetNearestSockets(nd, callPos)
            #Этот инструмент триггерится на любой выход
            if isBoth:
                self.foundGoalSkOut = list_fgSksOut[0] if list_fgSksOut else []
            #Получить вход по условиям:
            if not list_fgSksIn: #На ноды без входов триггериться.
                break #Все условия поиска нод пройдены. Покинуть цикл, потому что далее вход искать негде.
            skOut = self.foundGoalSkOut.tg if self.foundGoalSkOut else None
            if skOut: #Первый заход всегда isBoth=True, однако нод может не иметь выходов.
                #На этом этапе условия для отрицания просто найдут другой результат. "Присосётся не к этому, так к другому".
                for li in list_fgSksIn:
                    skIn = li.tg
                    #Для разрешённой-группы-между-собой разрешить "переходы". Рероутом для удобства можно в любой сокет с обоих сторон, минуя различные типы
                    tgl = (SkBetweenCheck(skIn.type))and(SkBetweenCheck(skOut.type))or(skOut.node.type=='REROUTE')or(skIn.node.type=='REROUTE')
                    #Любой сокет для виртуального выхода; разрешить в виртуальный для любого сокета; обоим в себя запретить
                    tgl = (tgl)or( (skIn.bl_idname=='NodeSocketVirtual')^(skOut.bl_idname=='NodeSocketVirtual') ) #|1|
                    #В версии 3.5 новый сокет автоматически не создаётся. Поэтому добавляются новые возможности по соединению
                    tgl = (tgl)or(skIn.node.type=='REROUTE')and(skIn.bl_idname=='NodeSocketVirtual')
                    #Если имена типов одинаковые, но не виртуальные
                    tgl = (tgl)or(skIn.bl_idname==skOut.bl_idname)and( not( (skIn.bl_idname=='NodeSocketVirtual')and(skOut.bl_idname=='NodeSocketVirtual') ) )
                    if tgl:
                        self.foundGoalSkIn = li
                        break #Без break'а goal'ом будет самый дальний от курсора, удовлетворяющий условиям.
                #На этом этапе условия для отрицания сделают результат никаким. Типа "ничего не нашлось", и будет обрабатываться соответствующим рисованием.
                if self.foundGoalSkIn:
                    if self.foundGoalSkOut.tg.node==self.foundGoalSkIn.tg.node: #Если для выхода ближайший вход -- его же нод.
                        self.foundGoalSkIn = None
                    elif self.foundGoalSkOut.tg.links: #Если выход уже куда-то подсоединён, даже если это выключенные линки.
                        for lk in self.foundGoalSkOut.tg.links:
                            if lk.to_socket==self.foundGoalSkIn.tg: #Если ближайший вход -- один из подсоединений выхода, то обнулить <=> "желаемое" соединение уже имеется
                                self.foundGoalSkIn = None
                                break #Используемый в проверке выше "self.foundGoalSkIn" обнуляется, поэтому нужно выходить, иначе будет попытка чтения из несуществующего элемента.
            break #Обработать нужно только первый ближайший, удовлетворяющий условиям.
    def modal(self, context, event):
        context.area.tag_redraw() #Ближайший нод в Debug'е находится(found) на "кадр" раньше, чем здесь. И я не знаю почему. Надеюсь не мой косяк.
        match event.type:
            case 'MOUSEMOVE':
                if context.space_data.edit_tree:
                    VoronoiLinker.NextAssessment(self, context, False)
                    if self.isMoveOut: #
                        self.foundGoalSkOut = None
                        VoronoiLinker.NextAssessment(self, context, True)
            case 'LEFT_SHIFT'|'SPACE': #Спасибо пользователю с ником "bzikarius" за банальную идею функционала "клавиши пробела".
                self.isMoveOut = event.value=='PRESS' #Пока что реализовано только для линкера, а там посмотрим.
            case self.keyType|'ESC':
                if event.value!='RELEASE':
                    return {'RUNNING_MODAL'}
                bpy.types.SpaceNodeEditor.draw_handler_remove(self.handle, 'WINDOW')
                if not context.space_data.edit_tree:
                    return {'FINISHED'}
                CrutchWithCollapseNode(None, 'In', True)
                CrutchWithCollapseNode(None, 'Out', True)
                if (self.foundGoalSkOut)and(self.foundGoalSkIn):
                    tree = context.space_data.edit_tree
                    #|2| Если дерево нодов от к.-н. аддона исчезло, то остатки имеют NodeUndefined и NodeSocketUndefined.
                    #Достаточно проверить только один из них, потому что они там все такие
                    if self.foundGoalSkOut.tg.bl_idname=='NodeSocketUndefined':
                        return {'CANCELLED'} #Через api линки на SocketUndefined строчкой ниже не создаваемы (но их можно создать вручную, очень странно), поэтому выходим.
                    #Чтобы можно было брать тип с рероута, который сам меняется под тип при соединении, типы сокетов перед соединением нужно запомнить
                    blIdSkOut, blIdSkIn = self.foundGoalSkOut.tg.bl_idname, self.foundGoalSkIn.tg.bl_idname
                    #См. |9| ...а его там неоткуда взять, ибо информация уже утеряна. Поэтому сохранить её здесь
                    headache = self.foundGoalSkOut.tg.node.inputs[0].bl_idname if self.foundGoalSkOut.tg.node.type=='REROUTE' else ''
                    #Самая важная строчка
                    lk = tree.links.new(self.foundGoalSkOut.tg, self.foundGoalSkIn.tg)
                    #"Фантомный" инпут может принимать в себя прям как мультиинпут, офигеть. Они даже могут между собой одним и тем же линком по нескольку раз связываться.
                    #Теперь под всё это нужно подстраиваться.
                    #Проверяем, если линк соединился на виртуальные, но "ничего не произошло".
                    #Но так же важно проверить, что этот виртуальный сокет не является рероутом
                    num = (blIdSkOut=='NodeSocketVirtual')*(lk.from_node.type!='REROUTE')+(blIdSkIn=='NodeSocketVirtual')*(lk.to_node.type!='REROUTE')*2
                    #Рероуты тоже могут быть виртуальными, поэтому нужно отличить их. "0" если io групп не найдено.
                    num *= (lk.from_node.bl_idname=='NodeGroupInput')or(lk.to_node.bl_idname=='NodeGroupOutput')
                    #Ситуация "виртуальный в виртуальный из группы в группу" исключена в |1| с помощью xor, от чего её не нужно обрабатывать.
                    def FullCopySkToSi(where, txt1, sk): #Вручную переносим значения из сокета в интерфейсный сокет.
                        si = getattr(tree, where).new(txt1, sk.name)
                        if getattr(si,'default_value',False):
                            si.default_value = sk.default_value # ! Не совершенно. Жаль я не знаю, как имитировать тру-соединение виртуального через api.
                        si.hide_value = sk.hide_value
                        if sk.bl_idname.find('Factor')!=-1:
                            si.min_value = 0.0
                            si.max_value = 1.0
                    match num:
                        case 1:
                            FullCopySkToSi('inputs', blIdSkIn, lk.to_socket) #Ручками добавляем новый io группы.
                            tree.links.remove(lk) #Удалить некорректный линк.
                            tree.links.new(self.foundGoalSkOut.tg.node.outputs[-2], self.foundGoalSkIn.tg) #Ручками создаём корректный линк.
                        case 2:
                            #|9| Головная боль. У ново созданных рероутов вывод всегда цвет, пока он не был подсоединён куда-н. Поэтому брать тип нужно с инпута рероута...
                            FullCopySkToSi('outputs', headache if headache else blIdSkOut, lk.from_socket)
                            tree.links.remove(lk)
                            tree.links.new(self.foundGoalSkOut.tg, self.foundGoalSkIn.tg.node.inputs[-2])
                        case 3: #Бесполезная редкая ситуация, которая обрабатывается лишь для полноты картины.
                            #Создавать новый io группы нужно только если соединение было в самый-последний-тру-виртуальный, определить это
                            if (lk.from_socket==lk.from_node.outputs[-1])and(lk.to_socket==lk.to_node.inputs[-1]): #Рероут всегда "-1"
                                tgl = lk.to_node.type=='REROUTE'
                                if tgl:
                                    nd = lk.from_node
                                    tree.inputs.new('NodeSocketVirtual', lk.to_socket.name)
                                else:
                                    nd = lk.to_node
                                    tree.outputs.new('NodeSocketVirtual', lk.from_socket.name)
                                tree.links.remove(lk)
                                if tgl: #Я не помню, для чего добавил tgl. Забыл написать комментарий об этом.
                                    tree.links.new(nd.outputs[-2], self.foundGoalSkIn.tg)
                                else:
                                    tree.links.new(self.foundGoalSkOut.tg, nd.inputs[-2])
                    #Моя личная хотелка, которая чинит странное поведение, и делает его логически-корректно-ожидаемым. Накой смысол последние соединённые api'м лепятся в начало?.
                    if self.foundGoalSkIn.tg.is_multi_input: #Если мультиинпут, то реализовать адекватный порядок подключения.
                        list_skLinks = []
                        for lk in self.foundGoalSkIn.tg.links: #Запомнить все имеющиеся линки по сокетам, и удалить их.
                            list_skLinks.append((lk.from_socket, lk.to_socket))
                            tree.links.remove(lk)
                        #До версии 3.5 обработка ниже нужна была, чтобы новый io группы дважды не создавался.
                        #Теперь без этой обработки Блендер или крашнется, или линк из виртуального в мультиинпут будет подсвечен красным как "некорректный"
                        if self.foundGoalSkOut.tg.bl_idname=='NodeSocketVirtual':
                            self.foundGoalSkOut.tg = self.foundGoalSkOut.tg.node.outputs[-2]
                        tree.links.new(self.foundGoalSkOut.tg, self.foundGoalSkIn.tg) #Соединить очередной первым.
                        for cyc in range(length(list_skLinks)-1): #Восстановить запомненные. "-1", потому что последний в списке является желанным что уже соединён строчкой выше.
                            tree.links.new(list_skLinks[cyc][0], list_skLinks[cyc][1])
                    return {'FINISHED'}
                return {'CANCELLED'}
        return {'RUNNING_MODAL'}
    def invoke(self, context, event):
        self.keyType = GetOpKey(VoronoiLinker.bl_idname)
        if not context.space_data.edit_tree:
            self.isTwo = True
            ToolInvokeStencilPrepare(self, context, EditTreeIsNoneDrawCallback)
        else:
            self.isMoveOut = False
            self.foundGoalSkOut = None
            self.foundGoalSkIn = None
            VoronoiLinker.NextAssessment(self, context, True)
            ToolInvokeStencilPrepare(self, context, VoronoiLinkerDrawCallback)
        return {'RUNNING_MODAL'}

def VoronoiPreviewerDrawCallback(self, context):
    if StartDrawCallbackStencil(self, context):
        return
    cusorPos = context.space_data.cursor_location
    if self.foundGoalSkOut:
        if Prefs().vpRvEeSksHighlighting:
            pos = VecWorldToRegScale(cusorPos)
            loc = Vector( (cusorPos.x+6*1000, cusorPos.y) )
            rd = (VecWorldToRegScale(loc)[0]-pos[0])/1000
            ndTar = self.foundGoalSkOut.tg.node
            for side in [False, True]:
                for skTar in ndTar.outputs if side else ndTar.inputs:
                    for lk in skTar.links:
                        if not lk.is_muted:
                            sk = lk.to_socket if side else lk.from_socket
                            nd = sk.node
                            if nd.type!='REROUTE':
                                list_fgSks = GetFromIoPuts(nd, 1-(side*2), context.space_data.cursor_location)
                                for li in list_fgSks:
                                    if li.tg==sk:
                                        DrawToolOftenStencil( cusorPos, [li], isDrawText=False, isDrawOnlyArea=True )
                                        DrawSkText( li.pos, ((li.tg.is_output*2-1), -.5), li, min(rd*4,30) )
                                        break
        DrawToolOftenStencil( cusorPos, [self.foundGoalSkOut], isLineToCursor=True, textSideFlip=True, isDrawText=True, isDrawMarkersMoreTharOne=True )
    elif Prefs().dsIsDrawPoint:
        DrawWidePoint(cusorPos)
class VoronoiPreviewer(bpy.types.Operator, VoronoiOpBase): # =VP=
    bl_idname = 'node.voronoi_previewer'
    bl_label = "Voronoi Previewer"
    bl_options = {'UNDO'}
    isPlaceAnAnchor: bpy.props.BoolProperty()
    def NextAssessment(self, context):
        isAncohorExist = context.space_data.edit_tree.nodes.get(voronoiAnchorName) #Если в геонодах есть якорь, то не триггериться только на геосокеты.
        #Некоторые пользователи в "начале знакомства" с аддоном захотят переименовать якорь.
        #Каждый призыв якоря одинаковый по заголовку, а при повторном призыве заголовок всё равно меняется обратно на стандартный.
        #После чего пользователи поймут, что переименовывать якорь бесполезно.
        if isAncohorExist: #Эта проверка с установкой лишь ускоряет процесс осознания.
            isAncohorExist.label = voronoiAnchorName
        isAncohorExist = not not isAncohorExist
        self.foundGoalSkOut = None #Нет нужды, но сбрасывается для ясности картины. Было полезно для отладки.
        callPos = context.space_data.cursor_location
        vpRvEeOnlyLinkedTrigger = Prefs().vpRvEeOnlyLinkedTrigger #Чтобы наверняка для ускорения, ибо 'Prefs().' меня смущает.
        for li in GetNearestNodes(context.space_data.edit_tree.nodes, callPos):
            nd = li.tg
            #Стандартное условие:
            if nd.type=='FRAME':
                continue
            if (nd.hide)and(nd.type!='REROUTE'):
                continue
            #Игнорировать готовый нод для переименования и <=> сохранения результата предпросмотра
            if Prefs().vpRvEeIsSavePreviewResults:
                if nd.name==voronoiPreviewResultNdName:
                    continue
            #Если в геометрических нодах, то игнорировать ноды без выходов геометрии
            if (context.space_data.tree_type=='GeometryNodeTree')and(not isAncohorExist):
                if not [sk for sk in nd.outputs if (sk.type=='GEOMETRY')and(not sk.hide)and(sk.enabled)]: #Искать сокеты геометрии, которые видимы.
                    continue
            #Пропускать ноды если визуально нет сокетов; или есть, но только виртуальные
            if not [sk for sk in nd.outputs if (not sk.hide)and(sk.enabled)and(sk.bl_idname!='NodeSocketVirtual')]:
                continue
            #Всё выше нужно было для того, чтобы точка не висела просто так и нод не мешал для удобного использования инструмента. По ощущениям получаются "прозрачные" ноды.
            #Игнорировать свой собственный спец-рероут-якорь (проверка на тип и имя)
            if ( (nd.type=='REROUTE')and(nd.name==voronoiAnchorName) ):
                continue
            #В случае успеха переходить к сокетам:
            list_fgSksIn, list_fgSksOut = GetNearestSockets(nd, callPos)
            for li in list_fgSksOut:
                #Этот инструмент триггерится на любой выход кроме виртуального. В геометрических нодах искать только выходы геометрии
                #Якорь притягивает на себя превиев. Рероут может принимать любой тип. Следовательно -- при наличии якоря отключаем триггер только на геосокеты
                if (li.tg.bl_idname!='NodeSocketVirtual')and( (context.space_data.tree_type!='GeometryNodeTree')or(li.tg.type=='GEOMETRY')or(isAncohorExist) ):
                    if (not(vpRvEeOnlyLinkedTrigger))or(li.tg.is_linked):
                        self.foundGoalSkOut = li
                        break #Обработать нужно только первый ближайший, удовлетворяющий условиям. Иначе будет самый дальний.
            if (not(vpRvEeOnlyLinkedTrigger))or(self.foundGoalSkOut):
                break #Точно так же, как и выше.
        if self.foundGoalSkOut:
            if Prefs().vpIsLivePreview:
                self.foundGoalSkOut.tg = DoPreview(context, self.foundGoalSkOut.tg) #Повторное присваивание нужно если в процессе сокет потеряется. См. |3|
            if Prefs().vpRvEeIsColorOnionNodes:
                for nd in context.space_data.edit_tree.nodes:
                    nd.use_custom_color = False
                nd = self.foundGoalSkOut.tg.node
                for sk in nd.inputs:
                    for lk in sk.links:
                        lk.from_socket.node.use_custom_color = True
                        lk.from_socket.node.color = (.55, .188, .188)
                for sk in nd.outputs:
                    for lk in sk.links:
                        lk.to_socket.node.use_custom_color = True
                        lk.to_socket.node.color = (.188, .188, .5)
    def modal(self, context, event):
        context.area.tag_redraw()
        match event.type:
            case 'MOUSEMOVE':
                if context.space_data.edit_tree:
                    VoronoiPreviewer.NextAssessment(self, context)
            case self.keyType|'ESC':
                if event.value!='RELEASE':
                    return {'RUNNING_MODAL'}
                bpy.types.SpaceNodeEditor.draw_handler_remove(self.handle, 'WINDOW')
                if not context.space_data.edit_tree:
                    return {'FINISHED'}
                if self.foundGoalSkOut:
                    DoPreview(context, self.foundGoalSkOut.tg)
                    if Prefs().vpRvEeIsColorOnionNodes:
                        for nd in context.space_data.edit_tree.nodes:
                            di = self.dict_saveRestoreNodeColors[nd]
                            nd.use_custom_color = di[0]
                            nd.color = di[1]
                return {'FINISHED'}
        return {'RUNNING_MODAL'}
    def invoke(self, context, event):
        self.keyType = GetOpKey(VoronoiPreviewer.bl_idname)
        if not context.space_data.edit_tree:
            if self.isPlaceAnAnchor:
                return {'FINISHED'}
            ToolInvokeStencilPrepare(self, context, EditTreeIsNoneDrawCallback)
            return {'RUNNING_MODAL'}
        if ('FINISHED' in bpy.ops.node.select('INVOKE_DEFAULT')): #Если симуляция выделения прошла успешно => что-то было выделено.
            match context.space_data.tree_type: #Если использование классического viewer'а разрешено, завершить оператор с меткой пропуска, "передавая эстафету" оригинальному виеверу.
                case 'CompositorNodeTree':
                    if Prefs().vpAllowClassicCompositorViewer:
                        return {'PASS_THROUGH'}
                case 'GeometryNodeTree':
                    if Prefs().vpAllowClassicGeoViewer:
                        return {'PASS_THROUGH'}
        if self.isPlaceAnAnchor:
            tree = context.space_data.edit_tree
            for nd in tree.nodes:
                nd.select = False
            ndRr = tree.nodes.get(voronoiAnchorName)
            tgl = not ndRr #Метка для обработки при первом появлении.
            ndRr = ndRr or tree.nodes.new('NodeReroute')
            tree.nodes.active = ndRr
            ndRr.name = voronoiAnchorName
            ndRr.label = ndRr.name
            ndRr.location = context.space_data.cursor_location
            ndRr.select = True
            if tgl: #Если уже существовал, то не выполнять код сохраняя уже имеющиеся линки рероута.
                #Почему бы и нет. Зато красивый. Установка напрямую rr.inputs[0].type = 'CUSTOM' не прокатывает
                nd = tree.nodes.new('NodeGroupInput')
                tree.links.new(nd.outputs[-1], ndRr.inputs[0])
                tree.nodes.remove(nd)
            return {'FINISHED'}
        else: #Иначе активация предпросмотра.
            self.foundGoalSkOut = None
            if Prefs().vpRvEeIsColorOnionNodes:
                self.dict_saveRestoreNodeColors = {}
                for nd in context.space_data.edit_tree.nodes:
                    self.dict_saveRestoreNodeColors[nd] = (nd.use_custom_color, nd.color.copy())
                    nd.use_custom_color = False
            VoronoiPreviewer.NextAssessment(self, context)
            ToolInvokeStencilPrepare(self, context, VoronoiPreviewerDrawCallback)
        return {'RUNNING_MODAL'}

tuple_shaderNodesWithColor = ('BSDF_ANISOTROPIC', 'BSDF_DIFFUSE',          'BSDF_GLASS',        'BSDF_GLOSSY',
                              'BSDF_HAIR',        'BSDF_HAIR_PRINCIPLED',  'PRINCIPLED_VOLUME', 'BACKGROUND',
                              'BSDF_REFRACTION' , 'SUBSURFACE_SCATTERING', 'BSDF_TOON',         'BSDF_TRANSLUCENT',
                              'BSDF_TRANSPARENT', 'BSDF_VELVET',           'VOLUME_ABSORPTION', 'VOLUME_SCATTER',
                              'BSDF_PRINCIPLED',  'EEVEE_SPECULAR',        'EMISSION')
def GetSocketIndex(sk): #Нашёл этот способ где-то на просторах blender.stackexchange.com
    return int(sk.path_from_id().split(".")[-1].split("[")[-1][:-1])
def DoPreview(context, goalSk):
    if not goalSk: #Для |3|, и просто общая проверка.
        return None
    context.space_data.edit_tree.nodes.active = goalSk.node #Для стабильности и ясности, а также для |6|
    def GetTrueTreeWay(context, nd):
        #NodeWrangler находил путь рекурсивно через активный нод дерева, используя "while tree.nodes.active != context.active_node:" (строка 613 в версии 3.43).
        #Этот способ имеет недостатки, ибо активным нодом может оказаться не нод-группа, банально тем, что можно открыть два окна редактора и спокойно нарушить этот "путь".
        #Погрузившись в документацию и исходный код я обнаружил простой api -- ".space_data.path". См. https://docs.blender.org/api/current/bpy.types.SpaceNodeEditorPath.html
        #Это "честный" api, дающий доступ для редактора узлов к пути от базы до финального дерева, отображаемого прямо сейчас.
        list_wayTreeNd = [ [ph.node_tree, ph.node_tree.nodes.active] for ph in reversed(context.space_data.path) ] #Путь реверсирован. 0-й -- целевой, последний -- корень
        #Как я могу судить, сама суть реализации редактора узлов не хранит >нод<, через который пользователь зашёл в группу (Но это не точно).
        #Поэтому если активным оказалась не нод-группа, то заменить на первый найденный по группе нод (или ничего, если не найдено)
        for cyc in range(1, length(list_wayTreeNd)):
            li = list_wayTreeNd[cyc]
            if (not li[1])or(li[1].type!='GROUP')or(li[1].node_tree!=list_wayTreeNd[cyc-1][0]): #Определить некорректного.
                li[1] = None #Если ниже не найден, то останется имеющийся неправильный. Поэтому обнулить его.
                for nd in li[0].nodes:
                    if (nd.type=='GROUP')and(nd.node_tree==list_wayTreeNd[cyc-1][0]): #Если в текущей глубине с неправильным нодом имеется нод группы с правильной группой.
                        li[1] = nd
                        break #Починка этой глубины произошла успешно.
        return list_wayTreeNd
    #Удалить все свои следы предыдущего использования для всех нод-групп, чей тип текущего редактора
    for ng in bpy.data.node_groups:
        if ng.bl_idname==context.space_data.tree_type:
            sk = True
            while sk: #Ищется по имени. Пользователь может дублировать выход. Без while они будут исчезать по одному каждое движение мыши.
                sk = ng.outputs.get(voronoiSkPreviewName)
                if sk:
                    ng.outputs.remove(sk)
    #|3| Переполучить сокет. Нужен в ситуациях присасывания к сокетам voronoiSkPreviewName, которые исчезли.
    if GetSocketIndex(goalSk)==-1: #Если сокет был удалён
        return None
    #Выстроить путь:
    curTree = context.space_data.edit_tree
    list_wayTreeNd = GetTrueTreeWay(context, goalSk.node)
    higWay = length(list_wayTreeNd)-1
    ixSkLastUsed = -1 #См. |4|
    isZeroPreviewGen = True #См. |5|
    for cyc in range(higWay+1):
        ndIn = None
        skOut = None
        skIn = None
        #Проверка по той же причине, по которой мне не нравится способ от NW.
        isPrecipice = (list_wayTreeNd[cyc][1]==None)and(cyc>0) #Обрыв обрабатывается на очередной глубине, ибо случай тривиален. Но не обрабатывается у корня, ибо догадайтесь сами.
        #Найти принимающий нод текущего уровня
        if (cyc!=higWay)and(not isPrecipice): #"not isPrecipice" -- в случае обрыва найти принимающий нод в коре, (а потом продолжить обработку обрыва).
            for nd in list_wayTreeNd[cyc][0].nodes:
                if (nd.type=='GROUP_OUTPUT')and(nd.is_active_output):
                    ndIn = nd
        else:
            match context.space_data.tree_type:
                case 'ShaderNodeTree':
                    for nd in list_wayTreeNd[higWay][0].nodes:
                        if nd.type in ('OUTPUT_MATERIAL','OUTPUT_WORLD','OUTPUT_LIGHT','OUTPUT_LINESTYLE','OUTPUT'):
                            if nd.is_active_output:
                                #Совать в сокет объёма если предпросматриваемый сокет имеет имя "Объём" и тип принимающего нода имеет вход для объёма
                                skIn = nd.inputs[ (goalSk.name=="Volume")*(nd.type in ('OUTPUT_MATERIAL','OUTPUT_WORLD')) ]
                case 'GeometryNodeTree':
                    for nd in list_wayTreeNd[higWay][0].nodes:
                        if (nd.type=='GROUP_OUTPUT')and(nd.is_active_output):
                            for sk in nd.inputs:
                                if sk.type=='GEOMETRY':
                                    skIn = sk
                                    break #Важно найти самый первый сверху.
                case 'CompositorNodeTree':
                    for nd in list_wayTreeNd[higWay][0].nodes:
                        if (nd.type=='VIEWER'):
                            skIn = nd.inputs[0]
                    if not skIn: #Если не нашёлся композиторский виевер, искать основной нод вывода.
                        for nd in list_wayTreeNd[higWay][0].nodes:
                            if (nd.type=='COMPOSITE'):
                                skIn = nd.inputs[0]
                case 'TextureNodeTree':
                    for nd in list_wayTreeNd[higWay][0].nodes:
                        if (nd.type=='OUTPUT'):
                            skIn = nd.inputs[0]
            if skIn: #Если найдено успешно, то установить нод из найденного сокета.
                ndIn = skIn.node
        if isPrecipice: #Если активный нод на пути удалился, то продолжать путь не от кого.
            #Можно просто выйти, а можно создать "группу перед обрывом" в корне и соединить.
            if skIn: #Наличие обрыва не означает, что корень точно будет. Он тоже может потеряться.
                tree = list_wayTreeNd[higWay][0]
                ndOut = None #Для того чтобы найти имеющийся или иначе создать.
                for nd in tree.nodes:
                    nd.select = False
                    if (nd.type=='GROUP')and(nd.node_tree==list_wayTreeNd[cyc-1][0]):
                        ndOut = nd
                        break
                ndOut = ndOut or tree.nodes.new(tree.bl_idname.replace("Tree", "Group"))
                ndOut.node_tree = list_wayTreeNd[cyc-1][0]
                tree.links.new(ndOut.outputs.get(voronoiSkPreviewName), skIn)
                ndOut.location = ndIn.location-Vector( (ndOut.width+20, 0) )
            return goalSk
        #Определить сокет отправляющего нода
        if cyc==0:
            skOut = goalSk
        else:
            skOut = list_wayTreeNd[cyc][1].outputs.get(voronoiSkPreviewName) #Получить по имени на очередной глубине.
            if (not skOut)and(ixSkLastUsed in range(length(list_wayTreeNd[cyc][1].outputs))): #Если нет своего превиева, то получить от |4|.
                skOut = list_wayTreeNd[cyc][1].outputs[ixSkLastUsed]
        #Определить сокет принимающего нода:
        #|4| Моё улучшающее изобретение -- если соединение уже имеется, то зачем создавать рядом такое же?.
        #Так же это эстетически комфортно. Так же это помогает отчистить последствия предпросмотра не выходя из целевой глубины.
        for lk in skOut.links: #Если этот сокет подсоединён куда-то.
            if lk.to_node==ndIn: #Если соединён с нодом для соединения.
                skIn = lk.to_socket #Выбрать его сокет => соединять с voronoiSkPreviewName не придётся, оно уже.
                ixSkLastUsed = GetSocketIndex(skIn) # И так может продолжаться до самого корня.
        #Если не удобный |4|, то создать очередной новый сокет для вывода
        if (not skIn)and(cyc!=higWay): #Вторая проверка нужна для ситуации если корень потерял вывод. В геонодах не страшно, но в других будет обработка "как есть".
            if context.space_data.tree_type=='GeometryNodeTree':
                txt = "NodeSocketGeometry"
            elif skOut.type=='SHADER':
                txt = "NodeSocketShader"
            else:
                #Почему цвет, а не шейдер, как у NW'а? Потому что иногда есть нужда вставить нод куда-то в пути превиева.
                #Но если линки шейдерные, то готовьтесь к разочарованию. Поэтому цвет; кой и был изначально у NW.
                txt = "NodeSocketColor"
            #Скрыть отображение значения у NodeSocketInterface, а не у конкретного нода в который соединяется
            list_wayTreeNd[cyc][0].outputs.new(txt, voronoiSkPreviewName).hide_value = True
            if not ndIn: #Если выводы групп куда-то потерялись, то создать его самостоятельно, вместо того чтобы остановиться и не знать, что делать.
                ndIn = list_wayTreeNd[cyc][0].nodes.new('NodeGroupOutput')
                #|6| Если потеря в целевой глубине, то нодом должен быть нод целевого сокета, а его там может не оказаться, ибо в пути содержится дерево и его активный нод.
                ndIn.location = list_wayTreeNd[cyc][1].location
                ndIn.location.x += list_wayTreeNd[cyc][1].width*2
            skIn = ndIn.inputs.get(voronoiSkPreviewName)
            isZeroPreviewGen = False
        #Удобный сразу-в-шейдер. (Такое же изобретение, как и |4|, только чуть менее удобное. Мб стоит избавиться от такой возможности)
        #Основной приём для шейдеров -- цвет, поэтому проверять нужно только для сокетов цвета.
        #Продолжить проверку если у корня есть вывод, и он куда-то подсоединён (может быть это окажется шейдер).
        if (Prefs().vpIsAutoShader)and(skOut.type=='RGBA')and(skIn)and(length(skIn.links)>0):
            #Мультиинпутов у корней не бывает, так что проверяется первый линк сокета. И если его нод находится в группе с "шейдерами что имеют цвет", то продолжить
            #|5| isZeroPreviewGen нужен, чтобы если просмотр из группы, то не соединятся в шейдер; но если это был "тру" путь без создания voronoiSkPreviewName, то из групп соединяться можно
            if (skIn.links[0].from_node.type in tuple_shaderNodesWithColor)and(isZeroPreviewGen):
                #Если сокет шейдера подсоединён только в корень
                if length(skIn.links[0].from_socket.links)==1:
                    #То тогда однозначный вариант определён, сменить сокет вывода с корня на сокет цвета шейдера. Повезло, что у всех шейдеров цвет именуется одинаково (почти у всех).
                    skIn = skIn.links[0].from_node.inputs.get("Color") or skIn.links[0].from_node.inputs.get("Base Color")
        #Соединить:
        #Якорь делает "планы изменились", и пересасывает поток на себя.
        ndRr = list_wayTreeNd[cyc][0].nodes.get(voronoiAnchorName)
        if ndRr:
            list_wayTreeNd[cyc][0].links.new(skOut, ndRr.inputs[0])
            break #Завершение после напарывания повышает возможности использования якоря, делая его ещё круче. Если у вас течка от Voronoi_Anchor, то я вас понимаю. У меня тоже.
            #Завершение позволяет иметь пользовательское соединение от глубины с якорем и до корня, не разрушая их (но сокеты предпросмотра всё равно создаются).
        elif (skOut)and(skIn): #Иначе обычное соединение маршрута.
            if Prefs().vpRvEeIsSavePreviewResults:
                tree = list_wayTreeNd[cyc][0]
                #Создать:
                nd = tree.nodes.get(voronoiPreviewResultNdName)
                tgl = not nd
                if (not tgl)and(nd.label!=voronoiPreviewResultNdName):
                    nd.name += "_"+nd.label
                    tgl = True
                if tgl:
                    nd = tree.nodes.new(tree.bl_idname.replace("Tree","")+'MixRGB') #"MixRGB" потому что он есть во всех редакторах, а ещё Shift+G > Type.
                nd.name = voronoiPreviewResultNdName
                nd.label = nd.name
                nd.use_custom_color = True
                nd.color = (.42968, .42968, .113725)
                nd.show_options = False
                nd.blend_type = 'ADD'
                nd.inputs[0].default_value = 0
                nd.inputs[1].default_value = (0.155927, 0.155927, 0.012286, 1.0)
                nd.inputs[0].hide = True
                nd.inputs[2].hide = True
                #Соединить:
                list_wayTreeNd[cyc][0].links.new(skOut, nd.inputs[1])
                list_wayTreeNd[cyc][0].links.new(nd.outputs[0], skIn)
                #Поставить:
                pos = skIn.node.location
                pos = [pos[0]+nd.width+40, pos[1]]
                nd.location = pos
            else:
                list_wayTreeNd[cyc][0].links.new(skOut, skIn)
    #Выделить предпросматриваемый нод
    if Prefs().vpIsSelectPreviewedNode:
        for nd in curTree.nodes:
            nd.select = False
        curTree.nodes.active = goalSk.node #Важно не только то, что только один он выделяется, но ещё и то, что он становится активным.
        goalSk.node.select = True
    return goalSk #Вернуть сокет. Нужно для |3|.

def VoronoiMixerDrawCallback(self, context):
    if StartDrawCallbackStencil(self, context):
        return
    def DrawMixerSkText(cusorPos, fg, ofsY, facY):
        txtDim = DrawSkText( cusorPos, (Prefs().dsDistFromCursor*(fg.tg.is_output*2-1), ofsY), fg )
        if (fg.tg.links)and(Prefs().dsIsDrawMarker):
            DrawIsLinkedMarker( cusorPos, [txtDim[0]*(fg.tg.is_output*2-1), txtDim[1]*facY*.75], GetSkCol(fg.tg) )
    cusorPos = context.space_data.cursor_location
    if self.foundGoalSkOut0:
        DrawToolOftenStencil( cusorPos, [self.foundGoalSkOut0], isLineToCursor=True, isDrawText=False )
        tgl = not not self.foundGoalSkOut1
        DrawMixerSkText(cusorPos, self.foundGoalSkOut0, -.5+.75*tgl, int(tgl))
        if tgl:
            DrawToolOftenStencil( cusorPos, [self.foundGoalSkOut1], isLineToCursor=True, isDrawText=False )
            DrawMixerSkText(cusorPos, self.foundGoalSkOut1, -1.25, -1)
    elif Prefs().dsIsDrawPoint:
        DrawWidePoint(cusorPos)
class VoronoiMixer(bpy.types.Operator, VoronoiOpBase): # =VM=
    bl_idname = 'node.voronoi_mixer'
    bl_label = "Voronoi Mixer"
    bl_options = {'UNDO'}
    def NextAssessment(self, context, isBoth):
        self.foundGoalSkOut1 = None #Важно обнулять; так же как и в линкере.
        callPos = context.space_data.cursor_location
        for li in GetNearestNodes(context.space_data.edit_tree.nodes, callPos):
            nd = li.tg
            #Стандартное условие:
            if nd.type=='FRAME':
                continue
            if (nd.hide)and(nd.type!='REROUTE'):
                continue
            #В фильтре нод нет нужды.
            list_fgSksIn, list_fgSksOut = GetNearestSockets(nd, callPos)
            #Этот инструмент триггерится на любой выход (ныне кроме виртуальных) для первого
            if isBoth: #Первый сокет устанавливается только один раз, второй ищется каждый раз.
                for li in list_fgSksOut:
                    if li.tg.bl_idname!='NodeSocketVirtual':
                        self.foundGoalSkOut0 = li
                        break
            #Для второго по условиям:
            skOut0 = self.foundGoalSkOut0.tg if self.foundGoalSkOut0 else None
            if skOut0:
                for li in list_fgSksOut:
                    skOut1 = li.tg
                    #Критерии были такие же, как и у Линкера. Но из-за того, что через api сокеты на виртуальные теперь не создаются, использование виртуальных для миксера выключено.
                    if (skOut1.bl_idname=='NodeSocketVirtual')or(skOut0.bl_idname=='NodeSocketVirtual'):
                        continue
                    if not( (SkBetweenCheck(skOut1.type))and(SkBetweenCheck(skOut0.type))or(skOut0.node.type=='REROUTE')or(skOut1.node.type=='REROUTE')or(skOut1.bl_idname==skOut0.bl_idname) ):
                        continue
                    self.foundGoalSkOut1 = li
                    break
                #Финальная проверка на корректность
                if self.foundGoalSkOut1:
                    if (skOut0==self.foundGoalSkOut1.tg):
                        self.foundGoalSkOut1 = None
            break
    def modal(self, context, event): #Можно я оставлю здесь свой ник с пробелами? u go rek. Потому что я так захотел.
        context.area.tag_redraw() #А пробелы нахрена? Чтобы через Ctrl+F случайно не найти. Говорю же, я так захотел. Не обращайте внимания.
        match event.type:
            case 'MOUSEMOVE':
                if context.space_data.edit_tree:
                    VoronoiMixer.NextAssessment(self, context, False)
            case self.keyType|'ESC':
                if event.value!='RELEASE':
                    return {'RUNNING_MODAL'}
                bpy.types.SpaceNodeEditor.draw_handler_remove(self.handle, 'WINDOW')
                if not context.space_data.edit_tree:
                    return {'FINISHED'}
                LSkCheckAll = lambda sk: sk.bl_idname in ('NodeSocketFloat','NodeSocketVector','NodeSocketInt','NodeSocketFloatFactor','NodeSocketVectorDirection')
                LSkCheckVec = lambda sk: sk.bl_idname in ('NodeSocketVector','NodeSocketVectorDirection')
                if (self.foundGoalSkOut0)and(self.foundGoalSkOut1):
                    mixerGlbVars.sk0 = self.foundGoalSkOut0.tg
                    mixerGlbVars.sk1 = self.foundGoalSkOut1.tg
                    #Поддержка виртуальных выключена, читается только из первого
                    mixerGlbVars.skType = mixerGlbVars.sk0.type# if mixerGlbVars.sk0.bl_idname!='NodeSocketVirtual' else mixerGlbVars.sk1.type
                    if Prefs().vmIsFastMathIncluded:
                        tgl0 = Prefs().vmFastMathActivationTrigger=='ALL'
                        tgl1 = LSkCheckAll(mixerGlbVars.sk0)
                        tgl2 = LSkCheckAll(mixerGlbVars.sk1)
                        #Для двух сокетов -- выбрать "вектор" если первый "вектор", или считать выбор со второго если первый не математический сокет
                        mixerGlbVars.isDisplayVec = LSkCheckVec(mixerGlbVars.sk0)or(not tgl1)and(LSkCheckVec(mixerGlbVars.sk1))
                        #tgl0 -- "исключающая" маска. Если оба сокета для "ALL" или один из них для "ANY"
                        if (tgl0)and(tgl1)and(tgl2)or(not tgl0)and( (tgl1)or(tgl2) ):
                            bpy.ops.node.voronoi_fastmath('INVOKE_DEFAULT')
                            return {'FINISHED'}
                    di = dict_dictTupleMixerMain.get(context.space_data.tree_type, False)
                    if not di: #Если не в классических редакторах, то просто выйти. Ибо классические у всех одинаковые, а аддонских есть бесчисленное множество.
                        return {'CANCELLED'}
                    di = di.get(mixerGlbVars.skType, False)
                    if di:
                        if length(di)==1: #Если выбор всего один, то пропустить его и сразу переходить к смешиванию.
                            DoMix(context, di[0])
                        else: #Иначе предоставить выбор
                            bpy.ops.wm.call_menu_pie(name="VL_MT_voronoi_mixer_pie")
                elif (self.foundGoalSkOut0)and(not self.foundGoalSkOut1)and(Prefs().vmIsFastMathIncluded): #См. |7|
                    mixerGlbVars.sk0 = self.foundGoalSkOut0.tg
                    mixerGlbVars.sk1 = None #Самая важная часть для вытягивания из одного сокета.
                    mixerGlbVars.isDisplayVec = LSkCheckVec(mixerGlbVars.sk0) #Для одного сокета -- выбор тривиален.
                    if LSkCheckAll(mixerGlbVars.sk0):
                        bpy.ops.node.voronoi_fastmath('INVOKE_DEFAULT')
                return {'FINISHED'}
        return {'RUNNING_MODAL'}
    def invoke(self, context, event):
        self.keyType = GetOpKey(VoronoiMixer.bl_idname)
        if not context.space_data.edit_tree:
            ToolInvokeStencilPrepare(self, context, EditTreeIsNoneDrawCallback)
        else:
            self.foundGoalSkOut0 = None
            self.foundGoalSkOut1 = None
            VoronoiMixer.NextAssessment(self, context, True)
            ToolInvokeStencilPrepare(self, context, VoronoiMixerDrawCallback)
        return {'RUNNING_MODAL'}

dict_dictTupleMixerMain = {                   #Порядок важен, самые частые(в этом списке) идут первее (кроме MixRGB).
        'ShaderNodeTree':     {'SHADER':     ('ShaderNodeMixShader','ShaderNodeAddShader'),
                               'VALUE':      ('ShaderNodeMixRGB',  'ShaderNodeMix',                      'ShaderNodeMath'),
                               'RGBA':       ('ShaderNodeMixRGB',  'ShaderNodeMix'),
                               'VECTOR':     ('ShaderNodeMixRGB',  'ShaderNodeMix',                                       'ShaderNodeVectorMath'),
                               'INT':        ('ShaderNodeMixRGB',  'ShaderNodeMix',                      'ShaderNodeMath')},

        'GeometryNodeTree':   {'VALUE':      ('GeometryNodeSwitch','ShaderNodeMix','FunctionNodeCompare','ShaderNodeMath'),
                               'RGBA':       ('GeometryNodeSwitch','ShaderNodeMix','FunctionNodeCompare'),
                               'VECTOR':     ('GeometryNodeSwitch','ShaderNodeMix','FunctionNodeCompare',                 'ShaderNodeVectorMath'),
                               'STRING':     ('GeometryNodeSwitch',                'FunctionNodeCompare',                                         'GeometryNodeStringJoin'),
                               'INT':        ('GeometryNodeSwitch','ShaderNodeMix','FunctionNodeCompare','ShaderNodeMath'),
                               'BOOLEAN':    ('GeometryNodeSwitch','ShaderNodeMixRGB',                   'ShaderNodeMath',                        'FunctionNodeBooleanMath'),
                               'OBJECT':     ('GeometryNodeSwitch',), # ^ для микса миксом болеана нужно слишком много дополнительных условий, так что не поддерживается.
                               'MATERIAL':   ('GeometryNodeSwitch',),
                               'COLLECTION': ('GeometryNodeSwitch',),
                               'TEXTURE':    ('GeometryNodeSwitch',),
                               'IMAGE':      ('GeometryNodeSwitch',),
                               'GEOMETRY':   ('GeometryNodeSwitch','GeometryNodeJoinGeometry','GeometryNodeInstanceOnPoints','GeometryNodeCurveToMesh','GeometryNodeMeshBoolean','GeometryNodeGeometryToInstance')},

        'CompositorNodeTree': {'VALUE':      ('CompositorNodeMixRGB','CompositorNodeSwitch','CompositorNodeSplitViewer','CompositorNodeSwitchView','CompositorNodeMath'),
                               'RGBA':       ('CompositorNodeMixRGB','CompositorNodeSwitch','CompositorNodeSplitViewer','CompositorNodeSwitchView',                      'CompositorNodeAlphaOver'),
                               'VECTOR':     ('CompositorNodeMixRGB','CompositorNodeSwitch','CompositorNodeSplitViewer','CompositorNodeSwitchView'),
                               'INT':        ('CompositorNodeMixRGB','CompositorNodeSwitch','CompositorNodeSplitViewer','CompositorNodeSwitchView','CompositorNodeMath')},

        'TextureNodeTree':    {'VALUE':      ('TextureNodeMixRGB','TextureNodeTexture','TextureNodeMath'),
                               'RGBA':       ('TextureNodeMixRGB','TextureNodeTexture'),
                               'VECTOR':     ('TextureNodeMixRGB',                                        'TextureNodeDistance'),
                               'INT':        ('TextureNodeMixRGB','TextureNodeTexture','TextureNodeMath')}}
dict_tupleMixerNodesDefs = { #"-1" означает визуальную здесь метку, что их подключения высчитываются автоматически (См. |8|), а не указаны явно в этом списке.
        'GeometryNodeSwitch':             (-1, -1, "Switch"),
        'ShaderNodeMix':                  (-1, -1, "Mix"),
        'FunctionNodeCompare':            (-1, -1, "Compare"),
        'ShaderNodeMath':                 (0, 1, "Max"),
        'ShaderNodeMixRGB':               (1, 2, "Mix RGB"),
        'CompositorNodeMixRGB':           (1, 2, "Mix"),
        'CompositorNodeSwitch':           (0, 1, "Switch"),
        'CompositorNodeSplitViewer':      (0, 1, "Split Viewer"),
        'CompositorNodeSwitchView':       (0, 1, "Switch View"),
        'TextureNodeMixRGB':              (1, 2, "Mix"),
        'TextureNodeTexture':             (0, 1, "Texture"),
        'ShaderNodeVectorMath':           (0, 1, "Max"),
        'CompositorNodeMath':             (0, 1, "Max"),
        'TextureNodeMath':                (0, 1, "Max"),
        'ShaderNodeMixShader':            (1, 2, "Mix"),
        'ShaderNodeAddShader':            (0, 1, "Add"),
        'GeometryNodeStringJoin':         (1, 1, "Join"),
        'FunctionNodeBooleanMath':        (0, 1, "Or"),
        'CompositorNodeAlphaOver':        (1, 2, "Alpha Over"),
        'TextureNodeDistance':            (0, 1, "Distance"),
        'GeometryNodeJoinGeometry':       (0, 0, "Join"),
        'GeometryNodeInstanceOnPoints':   (0, 2, "Instance on Points"),
        'GeometryNodeCurveToMesh':        (0, 1, "Curve to Mesh"),
        'GeometryNodeMeshBoolean':        (0, 1, "Boolean"),
        'GeometryNodeGeometryToInstance': (0, 0, "To Instance")}
def DoMix(context, txt):
    tree = context.space_data.edit_tree
    if not tree:
        return
    bpy.ops.node.add_node('INVOKE_DEFAULT', type=txt, use_transform=True)
    aNd = tree.nodes.active
    aNd.width = 140
    txt = {'VALUE':'FLOAT','INT':'FLOAT'}.get(mixerGlbVars.skType, mixerGlbVars.skType)
    match aNd.bl_idname: #Дважды switch case -- для комфортного кода и немного экономии.
        case 'ShaderNodeMath'|'ShaderNodeVectorMath'|'CompositorNodeMath'|'TextureNodeMath':
            aNd.operation = 'MAXIMUM'
        case 'FunctionNodeBooleanMath':
            aNd.operation = 'OR'
        case 'TextureNodeTexture':
            aNd.show_preview = False
        case 'GeometryNodeSwitch':
            aNd.input_type = txt
        case 'FunctionNodeCompare':
            aNd.data_type = txt
            aNd.operation = aNd.operation if aNd.data_type!='FLOAT' else 'EQUAL'
        case 'ShaderNodeMix':
            aNd.data_type = txt
    match aNd.bl_idname:
        case 'GeometryNodeSwitch'|'FunctionNodeCompare'|'ShaderNodeMix': #|8|
            tgl = aNd.bl_idname!='FunctionNodeCompare'
            #Для микса и переключателя искать с конца, потому что их сокеты для переключения имеют тип некоторых искомых. У нода сравнения всё наоборот.
            list_foundSk = [sk for sk in (reversed(aNd.inputs) if tgl else aNd.inputs) if sk.type=={'INT':'VALUE'}.get(mixerGlbVars.skType, mixerGlbVars.skType)]
            tree.links.new(mixerGlbVars.sk0, list_foundSk[tgl]) #Из-за направления поиска, нужно выбирать их из списка так же с учётом направления.
            tree.links.new(mixerGlbVars.sk1, list_foundSk[not tgl])
        case _:
            #Такая плотная суета ради мультиинпута -- для него нужно изменить порядок подключения:
            if aNd.inputs[dict_tupleMixerNodesDefs[aNd.bl_idname][0]].is_multi_input:
                tree.links.new( mixerGlbVars.sk1, aNd.inputs[dict_tupleMixerNodesDefs[aNd.bl_idname][1]] )
            tree.links.new( mixerGlbVars.sk0, aNd.inputs[dict_tupleMixerNodesDefs[aNd.bl_idname][0]] )
            if not aNd.inputs[dict_tupleMixerNodesDefs[aNd.bl_idname][0]].is_multi_input:
                tree.links.new( mixerGlbVars.sk1, aNd.inputs[dict_tupleMixerNodesDefs[aNd.bl_idname][1]] )
class VoronoiMixerMixer(bpy.types.Operator, VoronoiOpBase):
    bl_idname = 'node.voronoi_mixer_mixer'
    bl_label = "Voronoi Mixer Mixer"
    bl_options = {'UNDO'}
    txt: bpy.props.StringProperty()
    def execute(self, context):
        DoMix(context, self.txt)
        return {'FINISHED'}
class VoronoiMixerPie(bpy.types.Menu):
    bl_idname = 'VL_MT_voronoi_mixer_pie'
    bl_label = "" #Текст здесь будет отображаться в центре пирога.
    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.label( text={'VALUE':'Float','RGBA':'Color'}.get( mixerGlbVars.skType, mixerGlbVars.skType.capitalize() ) )
        for li in dict_dictTupleMixerMain[context.space_data.tree_type][mixerGlbVars.skType]:
            pie.operator('node.voronoi_mixer_mixer', text=dict_tupleMixerNodesDefs[li][2], translate=False).txt=li

#"FastMath" -- мой другой аддон, чьи возможности я принёс сюда, чтобы использовать их вместе с мощностью VoronoiLinker'а. Вся суть моей "быстрой математики" -- заполучить нод
# с нужной операцией через два пирога (почему два пирога, читайте далее). Здесь происходит тоже самое, только дополнительно с удобными связями благодаря VL'у.
#|7| Из-за того, что имеется возможность вызывать даже из однго сокета, быстрой математикой можно почти полноценно пользоваться и без моего основного аддона быстрой математики,
# ("почти", потому что иногда есть редкая нужда просто добавить нод с нужной операцией без авто-соединений, типа Shift A, но не выцеливать операцию из большого списка.
#  А так же потому, что здесь не получается использовать перетаскивание курсора для выбора сектора, нужно только кликать. А так же потому, что не выбрать и не вставить нод на линк).
#Для желающих избавиться от двойного пирога и сделать его одним -- пожалуйста. Прелесть пирога в том -- что в нём не нужно целиться. Его "кнопки" -- сектора, заполняют всё пространство,
# (прям как VL). Но от сего есть побочный эффект -- только 8 пунктов выбора, если больше -- секторность пирога станет слишком не удобной. Проблема 8-ми секторов -- очевидная и геометрическая,
# а значит я могу смело утверждать, что какую бы идею вы не придумали для сокращения двух пирогов до одного, вы будете вынуждены вернуться обратно в снайперское выцеливание курсором
# нужного пункта. Даже если кнопки будут очень большими, выцеливание никуда не денется. Вы не можете сделать свои кнопки больше, чем сектор пирога. Именно поэтому я пошёл на такую жертву --
# сделав двойной пирог. Ибо это вынужденная неизбежность -- вариантов операций математики больше, чем 8. И второе -- двойной пирог от этого свою ценность секторов не потерял,
# им всё ещё можно быстро и удобно пользоваться, так что не переломитесь.
#"Быстрая математика" на то и быстрая, что вы не напрягаете свой мозг и глаза, играя в игру "положи свой курсор в нужный прямоугольник среди десятков одинаковых".
#Пока я писал эти комментарии, внезапно понял ещё одну прелесть двойного пирога -- не перегруженность вариантами. Операций математики много, и вываливать их всех сразу, чтобы
# у вас глаза разбегались от такой паники -- такое себе удовольствие. К тому же вы вынуждены делать кнопки не прозрачными, в то время как кнопка-сектор-пирога догадайтесь сами.
#Спасибо за ваши геройские рвения по улучшению, но я буду пользоваться двойным пирогом.
#Хотите вишенку на торте? Пирог -- встроенная возможность Блендера. От чего нет нужды выстраивать свой огород велосипедов, с блек-джеком и костылями.
#ОБНОВЛЕНО:
#Неожиданно для меня оказалось, что пирог может рисовать обычный layout. От чего добавил дополнительный тип пирога "для контроля", что минует двойной пирог.
#P.s. двойной пирог всё равно круче.
tuple_tupleMathMap = (
        #Было бы не круто разбросать их бездумно, поэтому я пытался соблюсти некоторую логическую последовательность. Например, расставляя пары по смыслу диаметрально противоположными.
        #Пирог располагает в себе элементы следующим образом: лево, право, низ, верх, после чего классическое построчное заполнение.
        #"Compatible..." -- чтобы у векторов и у математики одинаковые операции были на одинаковых местах (кроме тригонометрических).
        ("Advanced",              ('SQRT',       'POWER',        'EXPONENT',   'LOGARITHM',   'INVERSE_SQRT','PINGPONG')),
        ("Compatible Primitives", ('SUBTRACT',   'ADD',          'DIVIDE'   ,  'MULTIPLY',    'ABSOLUTE',    'MULTIPLY_ADD')),
        ("Rounding",              ('SMOOTH_MIN', 'SMOOTH_MAX',   'LESS_THAN',  'GREATER_THAN','SIGN',        'COMPARE',     'TRUNC',  'ROUND')),
        ("Compatible Vector",     ('MINIMUM',    'MAXIMUM',      'FLOOR',      'FRACT',        'CEIL',       'MODULO',      'SNAP',   'WRAP')),
        ("", ()),
        ("", ()),
        ("Other",                 ('COSH',       'RADIANS',      'DEGREES',    'SINH',        'TANH')),
        ("Trigonometric",         ('SINE',       'COSINE',       'TANGENT',    'ARCTANGENT',  'ARCSINE',     'ARCCOSINE',   'ARCTAN2')))
tuple_tupleVecMathMap = (
        #За исключением примитивов, где прослеживается супер очевидная логика (право -- плюс -- add, лево -- минус -- sub; всё как на числовой оси),
        # лево и низ у меня имеют более высокую степень простоты, чем обратная сторона.
        #Например, length проще, чем distance. Всем же остальным не очевидным и не осе-ориентированным достаётся как получится.
        ("Advanced",              ('SCALE',      'NORMALIZE',    'LENGTH',     'DISTANCE',    'SINE',        'COSINE',      'TANGENT')),
        ("Compatible Primitives", ('SUBTRACT',   'ADD',          'DIVIDE',     'MULTIPLY',    'ABSOLUTE',    'MULTIPLY_ADD')),
        ("Rays",                  ('DOT_PRODUCT','CROSS_PRODUCT','PROJECT',    'FACEFORWARD', 'REFRACT',     'REFLECT')),
        ("Compatible Vector",     ('MINIMUM',    'MAXIMUM',      'FLOOR',      'FRACTION',    'CEIL',        'MODULO',      'SNAP',   'WRAP')),
        ("", ()),
        ("", ()),
        ("", ()),
        ("", ()))
#Ассоциация типа нода математики для типа редактора дерева
tuple_dictEditorMathNodes = ( {'ShaderNodeTree':     'ShaderNodeMath',
                               'GeometryNodeTree':   'ShaderNodeMath',
                               'CompositorNodeTree': 'CompositorNodeMath',
                               'TextureNodeTree':    'TextureNodeMath'},
                              {'ShaderNodeTree':   'ShaderNodeVectorMath',
                               'GeometryNodeTree': 'ShaderNodeVectorMath'} )
class FastMathMain(bpy.types.Operator, VoronoiOpBase): # =FM=
    bl_idname = 'node.voronoi_fastmath'
    bl_label = "Fast Maths"
    bl_options = {'UNDO'}
    operation: bpy.props.StringProperty() #Мост между глубинами вызова.
    def modal(self, context, event):
        #Раньше нужно было отчищать мост вручную, потому что он оставался равным последней записи; сейчас вроде не нужно.
        return {'FINISHED'}
    def invoke(self, context, event):
        tree = context.space_data.edit_tree
        if not tree:
            return {'CANCELLED'}
        def DispMenu(num):
            mixerGlbVars.displayDeep = num #Указывает пирогу, какую глубину вложенности он отображает. Нужно только для '.capitalize()'
            bpy.ops.wm.call_menu_pie(name="VL_MT_voronoi_fastmath_pie")
        tuple_who = tuple_tupleVecMathMap if mixerGlbVars.isDisplayVec else tuple_tupleMathMap
        mixerGlbVars.list_displayItems = [ti[0] for ti in tuple_who] #Установка списка здесь, нужна для elif ниже.
        if self.operation in (""," "): #Если вызов быстрой математики
            DispMenu(0)
        elif self.operation in mixerGlbVars.list_displayItems: #Если выбор категории
            #Вычленить список с операциями из "глобального" списка
            mixerGlbVars.list_displayItems = [ti[1] for ti in tuple_who if ti[0]==self.operation][0]
            DispMenu(1)
        else: #Иначе установка выбранной операции.
            txt = tuple_dictEditorMathNodes[mixerGlbVars.isDisplayVec].get(context.space_data.tree_type, "")
            if not txt: #Если нет в списке, то этот нод отсутствует в типе редактора => "смешивать" нечем.
                return {'CANCELLED'}
            #Ядро быстрой математики. Добавить нод и создать линки:
            bpy.ops.node.add_node('INVOKE_DEFAULT', type=txt, use_transform=True)
            aNd = tree.nodes.active
            aNd.operation = self.operation
            tree.links.new(mixerGlbVars.sk0, aNd.inputs[0])
            if mixerGlbVars.sk1: #Проверка нужна, чтобы можно было "вытягивать" быструю математику даже из одного сокета, см. |7|.
                #Второй ищется "визуально"; чтобы операция 'SCALE' корректно подсоединялась
                for cyc in range(1, length(aNd.inputs)):
                    if aNd.inputs[cyc].enabled:
                        tree.links.new(mixerGlbVars.sk1, aNd.inputs[cyc])
                    break #Нужно соединить только в первый попавшийся, иначе у 'MulAdd' будет соединено во все.
            #Обнулить содержимое второго сокета. Нужно для красоты; и вообще это математика.
            if not mixerGlbVars.isDisplayVec: #Теперь нод вектора уже создаётся по нулям, так что для него обнулять без нужды.
                for sk in aNd.inputs:
                    sk.default_value = 0.0
        return {'RUNNING_MODAL'}
class FastMathPie(bpy.types.Menu):
    bl_idname = 'VL_MT_voronoi_fastmath_pie'
    bl_label = "" #Текст здесь будет отображаться в центре пирога.
    def draw(self, context):
        pie = self.layout.menu_pie()
        if Prefs().vmFastMathPieType=='SPEED':
            for li in mixerGlbVars.list_displayItems:
                if not li:
                    row = pie.row()
                    continue
                #Автоматический перевод выключен, ибо оригинальные операции у нода математики так же не переводятся.
                pie.operator(FastMathMain.bl_idname, text=li.capitalize() if mixerGlbVars.displayDeep else li, translate=False).operation = li
        else:
            def AddFm(where, opt, ico='NONE'):
                where.operator(FastMathMain.bl_idname, text=opt.capitalize(), icon=ico, translate=False).operation = opt
            def GetCol(where):
                col = where.column()
                col.scale_x = (Prefs().vmFastMathPieScale-1)/2+1
                col.scale_y = Prefs().vmFastMathPieScale
                return col
            colLeft = GetCol(pie)
            colRight = GetCol(pie)
            colCenter = GetCol(pie)
            colLabel = GetCol(pie)
            box = colLabel.box()
            row = box.row()
            row.alignment = 'CENTER' #Не работает.
            #row.label(text=("Vector" if mixerGlbVars.isDisplayVec else "Float")+" Fast Math")
            row.label(text="Fast Math ("+("Vector" if mixerGlbVars.isDisplayVec else "Float")+")")
            AddFm(colRight, 'ADD',      'ADD')
            AddFm(colRight, 'SUBTRACT', 'REMOVE')
            AddFm(colRight, 'MULTIPLY', 'SORTBYEXT')
            AddFm(colRight, 'DIVIDE',   'ITALIC') #ITALIC  FIXED_SIZE  DECORATE_LINKED
            colRight.separator()
            AddFm(colRight, 'MULTIPLY_ADD')
            AddFm(colRight, 'ABSOLUTE')
            colRight.separator()
            for li in ['SINE', 'COSINE', 'TANGENT']:
                AddFm(colCenter, li, 'FORCE_HARMONIC')
            if not mixerGlbVars.isDisplayVec:
                for li in ['POWER', 'SQRT', 'EXPONENT', 'LOGARITHM', 'INVERSE_SQRT', 'PINGPONG']:
                    AddFm(colRight, li)
                colRight.separator()
                AddFm(colRight, 'RADIANS')
                AddFm(colRight, 'DEGREES')
                AddFm(colLeft, 'FRACT', 'IPO_LINEAR')
                for li in ['ARCTANGENT', 'ARCSINE', 'ARCCOSINE']:
                    AddFm(colCenter, li, 'RNA')
                for li in ['ARCTAN2', 'SINH', 'COSH', 'TANH']:
                    AddFm(colCenter, li)
            else:
                for li in ['SCALE', 'NORMALIZE', 'LENGTH', 'DISTANCE']:
                    AddFm(colRight, li)
                colRight.separator()
                AddFm(colLeft, 'FRACTION', 'IPO_LINEAR')
            AddFm(colLeft, 'FLOOR', 'IPO_CONSTANT')
            AddFm(colLeft, 'CEIL')
            AddFm(colLeft, 'MAXIMUM', 'NONE') #SORT_DESC  TRIA_UP_BAR
            AddFm(colLeft, 'MINIMUM', 'NONE') #SORT_ASC  TRIA_DOWN_BAR
            for li in ['MODULO', 'SNAP', 'WRAP']:
                AddFm(colLeft, li)
            colLeft.separator()
            if not mixerGlbVars.isDisplayVec:
                for li in ['GREATER_THAN', 'LESS_THAN', 'TRUNC', 'SIGN', 'SMOOTH_MAX', 'SMOOTH_MIN', 'ROUND', 'COMPARE']:
                    AddFm(colLeft, li)
            else:
                AddFm(colLeft, 'DOT_PRODUCT', 'LAYER_ACTIVE')
                AddFm(colLeft, 'CROSS_PRODUCT', 'ORIENTATION_LOCAL') #OUTLINER_DATA_EMPTY  ORIENTATION_LOCAL  EMPTY_ARROWS
                AddFm(colLeft, 'PROJECT', 'CURVE_PATH') #SNAP_OFF  SNAP_ON  MOD_SIMPLIFY  CURVE_PATH
                AddFm(colLeft, 'FACEFORWARD', 'ORIENTATION_NORMAL')
                AddFm(colLeft, 'REFRACT', 'NODE_MATERIAL') #MOD_OFFSET  NODE_MATERIAL
                AddFm(colLeft, 'REFLECT', 'INDIRECT_ONLY_OFF') #INDIRECT_ONLY_OFF  INDIRECT_ONLY_ON

#P.s. Инструменты здесь отсортированы в порядке убывания их "крутости".
def VoronoiSwaperDrawCallback(self, context):
    if StartDrawCallbackStencil(self, context):
        return
    def DrawMixerSkText(cusorPos, fg, ofsY, facY):
        txtDim = DrawSkText( cusorPos, (Prefs().dsDistFromCursor*(fg.tg.is_output*2-1), ofsY), fg )
        if (fg.tg.links)and(Prefs().dsIsDrawMarker):
            DrawIsLinkedMarker( cusorPos, [txtDim[0]*(fg.tg.is_output*2-1), txtDim[1]*facY*.75], GetSkCol(fg.tg) )
    cusorPos = context.space_data.cursor_location
    if self.foundGoalSkIo0:
        DrawToolOftenStencil( cusorPos, [self.foundGoalSkIo0], isLineToCursor=True, isDrawText=False )
        tgl = not not self.foundGoalSkIo1
        DrawMixerSkText(cusorPos, self.foundGoalSkIo0, -.5+.75*tgl, int(tgl))
        if tgl:
            DrawToolOftenStencil( cusorPos, [self.foundGoalSkIo1], isLineToCursor=True, isDrawText=False )
            DrawMixerSkText(cusorPos, self.foundGoalSkIo1, -1.25, -1)
    elif Prefs().dsIsDrawPoint:
        DrawWidePoint(cusorPos)
class VoronoiSwaper(bpy.types.Operator, VoronoiOpBase): # =VS=
    bl_idname = 'node.voronoi_swaper'
    bl_label = "Voronoi Swaper"
    bl_options = {'UNDO'}
    isAddMode: bpy.props.BoolProperty()
    def NextAssessment(self, context, isBoth):
        self.foundGoalSkIo1 = None #Важно обнулять; так же как и в линкере.
        callPos = context.space_data.cursor_location
        for li in GetNearestNodes(context.space_data.edit_tree.nodes, callPos):
            nd = li.tg
            #Стандартное условие:
            if nd.type=='FRAME':
                continue
            if (nd.hide)and(nd.type!='REROUTE'):
                continue
            #В фильтре нод нет нужды.
            list_fgSksIn, list_fgSksOut = GetNearestSockets(nd, callPos)
            #За основу взяты критерии от Миксера:
            if isBoth:
                fgSkOut, fgSkIn = None, None
                for li in list_fgSksOut:
                    if li.tg.bl_idname!='NodeSocketVirtual':
                        fgSkOut = li
                        break
                for li in list_fgSksIn:
                    if li.tg.bl_idname!='NodeSocketVirtual':
                        fgSkIn = li
                        break
                #Разрешить возможность "добавлять" и для входов тоже, но только для мультиинпутов, ибо очевидное
                if (self.isAddMode)and(fgSkIn):
                    #Проверка по типу, но не по `is_multi_input`, чтобы из обычного в мультиинпут можно было добавлять.
                    if (fgSkIn.tg.bl_idname not in ('NodeSocketGeometry','NodeSocketString')):#or(not fgSkIn.tg.is_multi_input): #Без второго условия больше возможностей.
                        fgSkIn = None
                self.foundGoalSkIo0 = MinFromFgs(fgSkOut, fgSkIn)
                #Здесь вокруг аккумулировалось много странных проверок с None и т.п. -- результат соединения вместе многих "типа высокоуровневых" функций, что я тут понаизобретал.
                #Расчихлять всё и спаивать вместе, теряя немного читабельности и повышая "типа производительность" (камон, это же питон) пока не хочется.
            skOut0 = self.foundGoalSkIo0.tg if self.foundGoalSkIo0 else None
            if skOut0:
                for li in list_fgSksOut if skOut0.is_output else list_fgSksIn:
                    skOut1 = li.tg
                    if (skOut1.bl_idname=='NodeSocketVirtual')or(skOut0.bl_idname=='NodeSocketVirtual'):
                        continue
                    self.foundGoalSkIo1 = li
                    break
                if self.foundGoalSkIo1:
                    if (skOut0==self.foundGoalSkIo1.tg):
                        self.foundGoalSkIo1 = None
            break
    def modal(self, context, event):
        context.area.tag_redraw()
        match event.type:
            case 'MOUSEMOVE':
                if context.space_data.edit_tree:
                    VoronoiSwaper.NextAssessment(self, context, False)
            case self.keyType|'ESC':
                if event.value!='RELEASE':
                    return {'RUNNING_MODAL'}
                bpy.types.SpaceNodeEditor.draw_handler_remove(self.handle, 'WINDOW')
                if not context.space_data.edit_tree:
                    return {'FINISHED'}
                if (self.foundGoalSkIo0)and(self.foundGoalSkIo1):
                    skIo0 = self.foundGoalSkIo0.tg
                    skIo1 = self.foundGoalSkIo1.tg
                    tree = context.space_data.edit_tree
                    tgl = skIo0.is_output #Проверка одинаковости is_output -- забота для NextAssessment
                    if not self.isAddMode:
                        #Поменять местами все соединения у первого и у второго сокета:
                        list_memSks = []
                        if tgl:
                            for lk in skIo0.links:
                                if lk.to_node!=skIo1.node: #Чтобы линк от нода не создался сам в себя. Проверять нужно у всех и таковые не обрабатывать.
                                    list_memSks.append(lk.to_socket)
                                    tree.links.remove(lk)
                            for lk in skIo1.links:
                                if lk.to_node!=skIo0.node: #^
                                    tree.links.new(skIo0, lk.to_socket)
                                    if lk.to_socket.is_multi_input: #Для мультиинпутов удалить.
                                        tree.links.remove(lk)
                            for li in list_memSks:
                                tree.links.new(skIo1, li)
                        else:
                            for lk in skIo0.links:
                                if lk.from_node!=skIo1.node: #^
                                    list_memSks.append(lk.from_socket)
                                    tree.links.remove(lk)
                            for lk in skIo1.links:
                                if lk.from_node!=skIo0.node: #^
                                    tree.links.new(lk.from_socket, skIo0)
                                    tree.links.remove(lk)
                            for li in list_memSks:
                                tree.links.new(li, skIo1)
                    else:
                        #Просто добавить линки с первого сокета на второй. Aka объединение, добавление.
                        if tgl:
                            for lk in skIo0.links:
                                if lk.to_node!=skIo1.node: #^
                                    tree.links.new(skIo1, lk.to_socket)
                                    if lk.to_socket.is_multi_input: #Без этого lk всё равно указывает на "добавленный" линк, от чего удаляется. Поэтому явная проверка для мультиинпутов.
                                        tree.links.remove(lk)
                        else: #Добавлено ради мультиинпутов.
                            for lk in skIo0.links:
                                if lk.from_node!=skIo1.node: #^
                                    tree.links.new(lk.from_socket, skIo1)
                                    tree.links.remove(lk)
                    return {'FINISHED'}
                return {'CANCELLED'}
        return {'RUNNING_MODAL'}
    def invoke(self, context, event):
        self.keyType = GetOpKey(VoronoiSwaper.bl_idname)
        if not context.space_data.edit_tree:
            ToolInvokeStencilPrepare(self, context, EditTreeIsNoneDrawCallback)
        else:
            self.foundGoalSkIo0 = None
            self.foundGoalSkIo1 = None
            VoronoiSwaper.NextAssessment(self, context, True)
            ToolInvokeStencilPrepare(self, context, VoronoiSwaperDrawCallback)
        return {'RUNNING_MODAL'}

#VoronoiHider нужен только для наведения порядка и эстетики в дереве.
#Для тех, кого (например меня) напрягают "торчащие без дела" пустые сокеты выхода, или нулевые (чьё значение 0.0, чёрный, и т.п.) незадействованные сокеты входа.
#Например, мне больно смотреть, как при манипуляции с "типа 2D" векторами у всех нодов "Combine-" и "SeparateXYZ" торчит этот "Z" сокет абсолютно без дела, когда контекст подразумевает только 2D.
#На самом деле история Hider'а такая же, как и у быстрой математики. Я припёр сюда свои помогалочки ради использоваться с мощностями VoronoiLinler'а.
#P.s. Если вы тоже хотите припереть сюда свою помогалочку, то милости прошу. Я весь аддон заботливо раскоментил тут всё подряд, в первую очередь чтобы самому не забыть.
# Просто скопируйте к.-н. имеющийся оператор или шаблон, и на его основе создайте свой.
def HideFromNode(nd, lastResult, isCanToggleHide=False):
    def CheckSkZeroDefaultValue(sk): #Shader, Geometry, Boolean и Virtual всегда True.
        match sk.type:
            case 'VALUE'|'INT':
                return sk.default_value==0
            case 'VECTOR'|'RGBA':
                return(sk.default_value[0]==0)and(sk.default_value[1]==0)and(sk.default_value[2]==0)
            case 'STRING':
                return sk.default_value==''
            case 'OBJECT'|'MATERIAL'|'COLLECTION'|'TEXTURE'|'IMAGE':
                return not sk.default_value
            case _:
                return True
    if lastResult: #Результат предыдущего анализа, есть ли сокеты чьё состояние изменилось бы. Нужно для isCanToggleHide
        def CheckAndDoForIo(where, f):
            success = False
            for sk in where:
                if (sk.enabled)and(not sk.links)and(f(sk)):
                    success = (success)or(not sk.hide)
                    if isCanToggleHide:
                        sk.hide = True
            return success
        tgl = False
        if nd.type=='GROUP_INPUT': #Проверка -- "хороший тон" оптимизации; строчка ниже нужна для LCheckOver.
            tgl = length([nd for nd in nd.id_data.nodes if nd.type=='GROUP_INPUT'])>1
        #Если виртуальные были созданы вручную, то у nd io групп не скрывать их. Потому что.
        LCheckOver = lambda sk: not( (sk.bl_idname=='NodeSocketVirtual')and
                                     (not tgl)and #Но если nd i групп больше одного, то всё равно скрывать.
                                     (sk.node.type in ('GROUP_INPUT','GROUP_OUTPUT'))and
                                     (GetSocketIndex(sk)!=length(sk.node.outputs if sk.is_output else sk.node.inputs)-1) )
        success = CheckAndDoForIo(nd.inputs, lambda sk: CheckSkZeroDefaultValue(sk)and(LCheckOver(sk)) )
        if [sk for sk in nd.outputs if (sk.enabled)and(sk.links)]: #Если хотя бы один сокет подсоединён во вне
            success = (CheckAndDoForIo(nd.outputs, lambda sk: LCheckOver(sk) ))or(success) #Здесь наоборот, чтобы функция гарантированно выполнилась.
        return success
    elif isCanToggleHide: #Иначе раскрыть всё.
        for att in ('inputs','outputs'):
            for sk in getattr(nd, att):
                sk.hide = False
def VoronoiHiderDrawCallback(self, context):
    if StartDrawCallbackStencil(self, context):
        return
    cusorPos = context.space_data.cursor_location
    if self.isHideSocket:
        if self.foundGoalTg:
            DrawToolOftenStencil( cusorPos, [self.foundGoalTg], isLineToCursor=True, textSideFlip=True )
        elif Prefs().dsIsDrawPoint:
            DrawWidePoint(cusorPos)
    else:
        if self.foundGoalTg:
            #Нод не имеет цвета (в этом аддоне вся тусовка ради сокетов, так что нод не имеет цвета, ок да?.)
            #Поэтому, для нода всё одноцветное -- белое или пользовательское.
            white = Vector( (1, 1, 1, 1) )
            if Prefs().dsIsDrawLine:
                col = white if Prefs().dsIsColoredLine else GetUniformColVec()
                DrawStick( self.foundGoalTg.pos, cusorPos, col, col )
            if Prefs().dsIsDrawPoint:
                DrawWidePoint( self.foundGoalTg.pos, white if Prefs().dsIsColoredPoint else GetUniformColVec() )
            tgl1 = Prefs().vhDrawNodeNameLabel in ('NAME', 'LABELNAME')
            tgl2 = Prefs().vhDrawNodeNameLabel in ('LABEL','LABELNAME')
            if (tgl1)or(tgl2):
                txt = self.foundGoalTg.tg.label
                tuple_ofsY = (.25,-1.25) if (txt)and(Prefs().vhDrawNodeNameLabel=='LABELNAME') else (-.5,-.5)
                col = white if Prefs().dsIsColoredSkText else GetUniformColVec()
                if Prefs().dsIsDrawSkText: #Именно, "Sk". Тут весь аддон про что?.
                    if tgl1:
                        DrawText( cusorPos, (Prefs().dsDistFromCursor, tuple_ofsY[0]), self.foundGoalTg.tg.name, col)
                    if (txt)and(tgl2):
                        DrawText( cusorPos, (Prefs().dsDistFromCursor, tuple_ofsY[1]), txt, col)
        elif Prefs().dsIsDrawPoint:
            DrawWidePoint(cusorPos)
class VoronoiHider(bpy.types.Operator, VoronoiOpBase): # =VH=
    bl_idname = 'node.voronoi_hider'
    bl_label = "Voronoi Hider"
    bl_options = {'UNDO'}
    isHideSocket: bpy.props.IntProperty()
    def NextAssessment(self, context):
        self.foundGoalTg = [] #Важно обнулять; так же как и в линкере.
        callPos = context.space_data.cursor_location
        for li in GetNearestNodes(context.space_data.edit_tree.nodes, callPos):
            nd = li.tg
            #Для этого инструмента рероуты так же пропускаются, по очевидным причинам.
            if (nd.hide)or(nd.type in ('FRAME','REROUTE')):
                continue
            self.foundGoalTg = li
            if self.isHideSocket:
                list_fgSksIn, list_fgSksOut = GetNearestSockets(nd, callPos)
                def GetNotLinked(list_sks): #Выдать первого, кто не имеет линков.
                    for li in list_sks:
                        if not li.tg.links: #Выключенный сокет всё равно учитывается.
                            return li
                fgSkIn = GetNotLinked(list_fgSksIn)
                fgSkOut = GetNotLinked(list_fgSksOut)
                if self.isHideSocket==1:
                    self.foundGoalTg = MinFromFgs(fgSkOut, fgSkIn)
                else:
                    self.foundGoalTg = fgSkIn
            else:
                if Prefs().vhIsToggleNodesOnDrag:
                    if self.firstResult is None:
                        self.firstResult = HideFromNode(self.foundGoalTg.tg, True)
                    HideFromNode(li.tg, self.firstResult, True)
            break
    def modal(self, context, event):
        context.area.tag_redraw()
        match event.type:
            case 'MOUSEMOVE':
                if context.space_data.edit_tree:
                    VoronoiHider.NextAssessment(self, context)
            case self.keyType|'ESC':
                if event.value!='RELEASE':
                    return {'RUNNING_MODAL'}
                bpy.types.SpaceNodeEditor.draw_handler_remove(self.handle, 'WINDOW')
                if not context.space_data.edit_tree:
                    return {'FINISHED'}
                if not self.foundGoalTg:
                    return {'CANCELLED'}
                match self.isHideSocket:
                    case 0: #Обработка нода.
                        if not Prefs().vhIsToggleNodesOnDrag:
                            #Во время сокрытия сокета нужно иметь информацию обо всех, поэтому выполняется дважды. В первый заход собирается, во второй выполняется.
                            HideFromNode(self.foundGoalTg.tg, HideFromNode(self.foundGoalTg.tg, True), True)
                    case 1: #Скрытие сокета.
                        self.foundGoalTg.tg.hide = True
                    case 2: #Переключение видимости значения сокета.
                        self.foundGoalTg.tg.hide_value = not self.foundGoalTg.tg.hide_value
                return {'FINISHED'}
        return {'RUNNING_MODAL'}
    def invoke(self, context, event):
        self.keyType = GetOpKey(VoronoiHider.bl_idname)
        if not context.space_data.edit_tree:
            ToolInvokeStencilPrepare(self, context, EditTreeIsNoneDrawCallback)
        else:
            self.foundGoalTg = []
            if Prefs().vhIsToggleNodesOnDrag:
                self.firstResult = None
            VoronoiHider.NextAssessment(self, context)
            ToolInvokeStencilPrepare(self, context, VoronoiHiderDrawCallback)
        return {'RUNNING_MODAL'}

#"Массовый линкер" -- как линкер, только много за раз (спасибо кэп). Наверное, самое редко-бесполезное что только можно было придумать здесь.
#Этот инструмент был создан только ради одной редкой и специфической нужды. В Блендере нет циклов, выход -- много одинаковых нод-групп подряд. И когда дело доходит до их соединения,
# нужно соединить мильон одинаковых сокетов у такого же количества нодов. Оптимизация -- соединить всё у двух, а потом копирование с бинарным ростом, но "пограничные случаи"
# всё равно нужно соединять ручками. Этот инструмент -- "из пушки по редким птичкам", крупица удобного наслаждения один раз в сто лет.
#См. вики на гитхабе, что бы посмотреть 4 примера использования массового линкера. Дайте мне знать, если обнаружите ещё одно необычное применение этому инструменту.
def VoronoiMassLinkerDrawCallback(self, context): # =VML=
    if StartDrawCallbackStencil(self, context):
        return
    cusorPos = context.space_data.cursor_location
    if not self.ndGoalOut:
        DrawDoubleNone(self, context)
    elif (self.ndGoalOut)and(not self.ndGoalIn):
        list_sks = GetNearestSockets(self.ndGoalOut, cusorPos)[1] #Взять только сокеты вывода.
        if not list_sks:
            DrawDoubleNone(self, context)
        for li in list_sks: #Не известно, к кому это будет подсоединено и к кому получится => рисовать от всех сокетов.
            DrawToolOftenStencil( cusorPos, [li], isLineToCursor=Prefs().dsIsAlwaysLine, isDrawText=False ) #Всем к курсору!
    else:
        self.list_equalFgSks = []
        for liSko in GetNearestSockets(self.ndGoalOut, cusorPos)[1]:
            for liSki in GetNearestSockets(self.ndGoalIn, cusorPos)[0]:
                #Т.к. "массовый" -- критерии приходится автоматизировать и сделать их едиными для всех.
                #Соединяться только с одинаковыми по именам сокетами
                if (liSko.tg.name==liSki.tg.name):
                    tgl = False
                    if Prefs().vlIsIgnoreExistingLinks: #Если соединяться без разбору, то исключить уже имеющиеся "желанные" связи. Нужно только для эстетики.
                        for lk in liSki.tg.links:
                            #Проверка is_linked нужна, чтобы можно было включить выключенные линки, перезаменив их.
                            if (lk.from_socket.is_linked)and(lk.from_socket==liSko.tg):
                                tgl = True
                        tgl = not tgl
                    else: #Иначе "уважать" уже соединённых.
                        tgl = not liSki.tg.links
                    if tgl:
                        self.list_equalFgSks.append( (liSko,liSki) )
                    continue
        if not self.list_equalFgSks:
            DrawWidePoint(cusorPos)
        for li in self.list_equalFgSks:
            #Т.к. поиск по именам, рисоваться здесь и подсоединяться ниже возможно из двух (и больше) сокетов в один и тот же одновременно.
            #  Типа "конфликт" одинаковых имён. Не является проблемой, а также не чинится из-за |10|.
            DrawToolOftenStencil( cusorPos, [li[0],li[1]], isDrawText=False )
#Здесь нарушается местный шаблон чтения-записи, и DrawCallback ищет и пишет в список найденные сокеты вместо того, чтобы просто читать и рисовать. Мне показалось, что так реализация проще,
#|10| Этот инструмент слишком странный и редко используемый, чтобы париться о грамотной реализации.
class VoronoiMassLinker(bpy.types.Operator, VoronoiOpBase):
    bl_idname = 'node.voronoi_mass_linker'
    bl_label = "Voronoi MassLinker"
    bl_options = {'UNDO'}
    def NextAssessment(self, context, isBoth):
        callPos = context.space_data.cursor_location
        for li in GetNearestNodes(context.space_data.edit_tree.nodes, callPos):
            nd = li.tg
            if nd.type=='FRAME':
                continue
            #Помимо свёрнутых так же игнорируются и рероуты, потому что у них инпуты всегда одни и с одинаковыми названиями
            if (nd.hide)or(nd.type=='REROUTE'):
                continue
            self.ndGoalIn = nd
            if isBoth:
                self.ndGoalOut = nd #Здесь нод-вывод устанавливается один раз.
            break
        if self.ndGoalOut==self.ndGoalIn: #Точно так же, как и в линкере, чтобы сам в себя не совался.
            self.ndGoalIn = None #Здесь нод-вход обнуляется каждый раз в случае неудачи.
    def modal(self, context, event):
        context.area.tag_redraw()
        match event.type:
            case 'MOUSEMOVE':
                if context.space_data.edit_tree:
                    VoronoiMassLinker.NextAssessment(self, context, False)
            case self.keyType|'ESC':
                if event.value!='RELEASE':
                    return {'RUNNING_MODAL'}
                bpy.types.SpaceNodeEditor.draw_handler_remove(self.handle, 'WINDOW')
                if not context.space_data.edit_tree:
                    return {'FINISHED'}
                if (self.ndGoalOut)and(self.ndGoalIn):
                    tree = context.space_data.edit_tree
                    #Проверка на потерянный редактор
                    if (self.list_equalFgSks)and(self.list_equalFgSks[0][0].tg.bl_idname=='NodeSocketUndefined'):
                        return {'CANCELLED'}
                    #Соединить всех!
                    for li in self.list_equalFgSks:
                        tree.links.new(li[0].tg, li[1].tg)
                    return {'FINISHED'}
                return {'CANCELLED'}
        return {'RUNNING_MODAL'}
    def invoke(self, context, event):
        self.keyType = GetOpKey(VoronoiMassLinker.bl_idname)
        if not context.space_data.edit_tree:
            self.isTwo = True
            ToolInvokeStencilPrepare(self, context, EditTreeIsNoneDrawCallback)
        else:
            self.ndGoalOut = None
            self.ndGoalIn = None
            self.list_equalFgSks = [] #Однажды странным образом modal() не смог найти этот атрибут в себе. Дублировал сюда.
            VoronoiMassLinker.NextAssessment(self, context, True)
            ToolInvokeStencilPrepare(self, context, VoronoiMassLinkerDrawCallback)
        return {'RUNNING_MODAL'}

#Шаблон для быстрого и удобного добавления нового инструмента:
def VoronoiDummyDrawCallback(self, context):
    if StartDrawCallbackStencil(self, context):
        return
    cusorPos = context.space_data.cursor_location
    if self.foundGoalSkIo:
        DrawToolOftenStencil( cusorPos, [self.foundGoalSkIo], isLineToCursor=True, textSideFlip=True )
    elif Prefs().dsIsDrawPoint:
        DrawWidePoint(cusorPos)
class VoronoiDummy(bpy.types.Operator, VoronoiOpBase): # =VD=
    bl_idname = 'node.voronoi_dummy'
    bl_label = "Voronoi Dummy"
    bl_options = {'UNDO'}
    def NextAssessment(self, context):
        self.foundGoalSkIo = None
        callPos = context.space_data.cursor_location
        for li in GetNearestNodes(context.space_data.edit_tree.nodes, callPos):
            nd = li.tg
            if nd.type=='FRAME':
                continue
            if (nd.hide)and(nd.type!='REROUTE'):
                continue
            list_fgSksIn, list_fgSksOut = GetNearestSockets(nd, callPos)
            fgSkIn = list_fgSksIn[0] if list_fgSksIn else None
            fgSkOut = list_fgSksOut[0] if list_fgSksOut else None
            self.foundGoalSkIo = MinFromFgs(fgSkOut, fgSkIn)
            break
    def modal(self, context, event):
        context.area.tag_redraw()
        match event.type:
            case 'MOUSEMOVE':
                if context.space_data.edit_tree:
                    VoronoiDummy.NextAssessment(self, context)
            case self.keyType|'ESC':
                if event.value!='RELEASE':
                    return {'RUNNING_MODAL'}
                bpy.types.SpaceNodeEditor.draw_handler_remove(self.handle, 'WINDOW')
                if not context.space_data.edit_tree:
                    return {'FINISHED'}
                if True: #Здесь проверка на существование целей.
                    if self.foundGoalSkIo:
                        self.foundGoalSkIo.tg.name = 'Hello world!'
                        self.foundGoalSkIo.tg.node.label = 'Hello world!'
                    return {'FINISHED'}
                return {'CANCELLED'}
        return {'RUNNING_MODAL'}
    def invoke(self, context, event):
        self.keyType = GetOpKey(VoronoiDummy.bl_idname)
        if not context.space_data.edit_tree:
            ToolInvokeStencilPrepare(self, context, EditTreeIsNoneDrawCallback)
        else:
            self.foundGoalSkIo = None
            VoronoiDummy.NextAssessment(self, context)
            ToolInvokeStencilPrepare(self, context, VoronoiDummyDrawCallback)
        return {'RUNNING_MODAL'}


voronoiAddonName = "VoronoiLinker"

def Prefs():
    return bpy.context.preferences.addons[voronoiAddonName].preferences

class VoronoiAddonTabs(bpy.types.Operator): #См. |11|
    bl_idname = 'node.voronoi_addon_tabs'
    bl_label = "Voronoi Addon Tabs"
    toTab: bpy.props.StringProperty()
    def execute(self, context):
        Prefs().vaUiTabs = self.toTab
        return {'FINISHED'}
class VoronoiAddonPrefs(bpy.types.AddonPreferences):
    bl_idname = voronoiAddonName if __name__=="__main__" else __name__
    #AddonPrefs
    vaUiTabs: bpy.props.EnumProperty(name="Addon Prefs Tabs", default='SETTINGS', items=( ('SETTINGS',"Settings",""),
                                                                                          ('DRAW',    "Draw",    ""),
                                                                                          ('KEYMAP',  "Keymap",  "") ))
    #Draw
    dsUniformColor: bpy.props.FloatVectorProperty(name="Alternative uniform Color", default=(.632502, .408091, .174378, .9), min=0, max=1, size=4, subtype='COLOR') #(.65, .65, .65, 1.0)
    #
    dsFontFile: bpy.props.StringProperty(name="Font File", default='C:\Windows\Fonts\consola.ttf', subtype='FILE_PATH')
    #
    dsPointOffsetX: bpy.props.FloatProperty(name="Point offset X axis", default=20, min=-50, max=50)
    dsFrameOffset:  bpy.props.IntProperty(name=  "Frame Size",          default=0,  min=0,   max=24, subtype='FACTOR')
    dsFontSize:     bpy.props.IntProperty(name=  "Font Size",           default=28, min=10,  max=48)
    #
    dsIsDrawSkText: bpy.props.BoolProperty(name="Text",        default=True)
    dsIsDrawMarker: bpy.props.BoolProperty(name="Markers",     default=True)
    dsIsDrawPoint:  bpy.props.BoolProperty(name="Points",      default=True)
    dsIsDrawLine:   bpy.props.BoolProperty(name="Line",        default=True)
    dsIsDrawSkArea: bpy.props.BoolProperty(name="Socket area", default=True)
    #
    dsIsColoredSkText: bpy.props.BoolProperty(name="Text",        default=True)
    dsIsColoredMarker: bpy.props.BoolProperty(name="Markers",     default=True)
    dsIsColoredPoint:  bpy.props.BoolProperty(name="Points",      default=True)
    dsIsColoredLine:   bpy.props.BoolProperty(name="Line",        default=True)
    dsIsColoredSkArea: bpy.props.BoolProperty(name="Socket area", default=True)
    #
    dsDisplayStyle: bpy.props.EnumProperty(name="Display Frame Style", default='CLASSIC', items=( ('CLASSIC',   "Classic",   "1"), #Если существует способ указать порядок
                                                                                                  ('SIMPLIFIED',"Simplified","2"), # и чтобы работало -- дайте знать.
                                                                                                  ('ONLYTEXT',  "Only text", "3") ))
    dsLineWidth:      bpy.props.IntProperty(name=  "Line Width",                default=1,  min=1, max=16, subtype="FACTOR")
    dsPointRadius:    bpy.props.FloatProperty(name="Point size",                default=1,  min=0, max=3)
    dsDistFromCursor: bpy.props.FloatProperty(name="Text distance from cursor", default=25, min=5, max=50)
    #
    dsIsAllowTextShadow: bpy.props.BoolProperty(name=       "Enable Text Shadow", default=True)
    dsShadowCol:         bpy.props.FloatVectorProperty(name="Shadow Color",       default=[0.0, 0.0, 0.0, .5], size=4, min=0,   max=1, subtype='COLOR')
    dsShadowOffset:      bpy.props.IntVectorProperty(name=  "Shadow Offset",      default=[2,-2],              size=2, min=-20, max=20)
    dsShadowBlur:        bpy.props.IntProperty(name=        "Shadow Blur",        default=2,                           min=0,   max=2)
    #
    dsIsAlwaysLine:     bpy.props.BoolProperty(name="Always draw line for VoronoiLinker", default=False)
    dsIsDrawDebug:      bpy.props.BoolProperty(name="Display debugging",                  default=False)
    # =====================================================================================================================================================
    #Linker
    vlAllowCrutchWithCollapsedNode: bpy.props.BoolProperty(name="Allow crutch with collapsed node", default=False)
    #Preview:
    vpAllowClassicCompositorViewer: bpy.props.BoolProperty(name="Allow using classic Compositor Viewer", default=False)
    vpAllowClassicGeoViewer:        bpy.props.BoolProperty(name="Allow using classic GeoNodes Viewer",   default=True)
    #
    vpIsAutoShader:          bpy.props.BoolProperty(name="Socket color directly into a shader", default=True)
    vpIsLivePreview:         bpy.props.BoolProperty(name="Live Preview",                        default=True)
    vpIsSelectPreviewedNode: bpy.props.BoolProperty(name="Select Previewed Node",               default=True)
    #
    vpRvEeIsColorOnionNodes:    bpy.props.BoolProperty(name="Node Onion Colors",               default=False)
    vpRvEeOnlyLinkedTrigger:    bpy.props.BoolProperty(name="Trigger only on linked",          default=False)
    vpRvEeSksHighlighting:      bpy.props.BoolProperty(name="Topology connected highlighting", default=False)
    vpRvEeIsSavePreviewResults: bpy.props.BoolProperty(name="Save preview results",            default=False) #Слишком лениво, пока забил. А там посмотрим.
    #Fast math:
    vmIsFastMathIncluded:  bpy.props.BoolProperty(name="Include Fast Math Pie", default=True)
    vmFastMathPieScale:    bpy.props.FloatProperty(name="Pie scale",            default=1.5, min=1, max=2, subtype="FACTOR")
    #
    vmFastMathActivationTrigger: bpy.props.EnumProperty(name="Activation trigger", default='ANY', items=( ('ANY',"At least one is a math socket",""),
                                                                                                          ('ALL',"Everyone is a math socket",    "") ))
    vmFastMathPieType: bpy.props.EnumProperty(name="Pie Type", default='CONTROL', items=( ('SPEED',  "Speed",  ""),
                                                                                          ('CONTROL',"Control","") ))
    #Hider:
    vhDrawNodeNameLabel: bpy.props.EnumProperty(name="Display text for node", default='NONE', items=( ('NONE',     "None",          ""),
                                                                                                      ('NAME',     "Only name",     ""),
                                                                                                      ('LABEL',    "Only label",    ""),
                                                                                                      ('LABELNAME',"Name and label","") ))
    vhIsToggleNodesOnDrag: bpy.props.BoolProperty(name="Toggle nodes on drag", default=True)
    #MassLinker
    vlIsIgnoreExistingLinks: bpy.props.BoolProperty(name="Ignore existing links", default=True)
    #
    def draw_tabSettings(self, context, where):
        col1 = where.column(align=True)
        #Эти две настройки слишком важные и "мощные", ибо VL дерзко перебевает классические Viewer'ы.
        #Чтобы это выглядело чуть менее чем "ты берега попутал?", они вынесены из коробки, а так же помещены в самое начало (да ещё и на вкладке по умолчанию).
        col1.prop(self,'vpAllowClassicCompositorViewer')
        col1.prop(self,'vpAllowClassicGeoViewer')
        box = where.box()
        col2 = box.column(align=True)
        ##
        col2.label(text="Voronoi Linker settings:")
        col2.prop(self,'vlAllowCrutchWithCollapsedNode')
        box = where.box()
        col2 = box.column(align=True)
        ##
        col2.label(text="Voronoi Preview settings:")
        col2.prop(self,'vpIsAutoShader')
        col2.prop(self,'vpIsLivePreview')
        col2.prop(self,'vpIsSelectPreviewedNode')
        box = col2.box()
        col3 = box.column(align=True)
        col3.label(text="Visual assistance in reverse engineering:")
        col3.prop(self,'vpRvEeIsColorOnionNodes')
        col3.prop(self,'vpRvEeOnlyLinkedTrigger')
        col3.prop(self,'vpRvEeSksHighlighting')
        row = col3.row(align=True)
        row.prop(self,'vpRvEeIsSavePreviewResults')
        row.active = False
        box = where.box()
        col2 = box.column(align=True)
        ##
        col2.label(text="Voronoi Mixer settings:")
        box = col2.box()
        col3 = box.column(align=True)
        col3.prop(self,'vmIsFastMathIncluded')
        col4 = col3.column(align=True).column()
        col4.active = self.vmIsFastMathIncluded
        col4.use_property_split = True
        col4.prop(self,'vmFastMathActivationTrigger')
        col4.prop(self,'vmFastMathPieType')
        col4 = col4.column(align=True)
        col4.prop(self,'vmFastMathPieScale')
        col4.active = self.vmFastMathPieType=='CONTROL'
        box = where.box()
        col2 = box.column(align=True)
        ##
        col2.label(text="Voronoi Hider settings:")
        col2.use_property_split = True
        col2.prop(self,'vhDrawNodeNameLabel')
        col2.use_property_split = False
        col2.prop(self,'vhIsToggleNodesOnDrag')
        box = where.box()
        col2 = box.column(align=True)
        ##
        col2.label(text="Voronoi MassLinker settings:")
        col2.prop(self,'vlIsIgnoreExistingLinks')

    def draw_tabDraw(self, context, where):
        col1 = where.column(align=True)
        row0 = col1.row(align=True)
        row0.use_property_split = True
        spl = row0.column(heading='Draw')
        spl.prop(self,'dsIsDrawSkText')
        spl.prop(self,'dsIsDrawMarker')
        spl.prop(self,'dsIsDrawPoint')
        spl.prop(self,'dsIsDrawLine')
        spl.prop(self,'dsIsDrawSkArea')
        spl = row0.column(heading='Colored')
        def FastPropWithActive(where, txt): #Выключено
            row = where.row(align=True)
            row.prop(self, txt)
            row.active = True or getattr(self, txt.replace("Colored","Draw"))
        FastPropWithActive(spl,'dsIsColoredSkText')
        FastPropWithActive(spl,'dsIsColoredMarker')
        FastPropWithActive(spl,'dsIsColoredPoint')
        FastPropWithActive(spl,'dsIsColoredLine')
        FastPropWithActive(spl,'dsIsColoredSkArea')
        col1.use_property_split = True
        col1.prop(self,'dsIsAlwaysLine')
        if ( (self.dsIsDrawSkText and not self.dsIsColoredSkText)or
             (self.dsIsDrawMarker and not self.dsIsColoredMarker)or
             (self.dsIsDrawPoint  and not self.dsIsColoredPoint )or
             (self.dsIsDrawLine   and not self.dsIsColoredLine  )or
             (self.dsIsDrawSkArea and not self.dsIsColoredSkArea) ):
            col1.prop(self, 'dsUniformColor')
        col1.separator()
        col1.prop(self,'dsDisplayStyle')
        col1 = where.column(align=True)
        col1.use_property_split = True
        col1.prop(self,'dsFontFile')
        import os
        if not os.path.splitext(self.dsFontFile)[1] in (".ttf",".otf"):
            spl = col1.split(factor=.4, align=True)
            spl.label(text="")
            spl.label(text="Only .ttf or .otf format", icon='ERROR')
        col1.separator()
        col1.prop(self,'dsLineWidth')
        col1.prop(self,'dsPointRadius')
        col1.prop(self,'dsFontSize')
        col1 = where.column(align=True)
        col1.use_property_split = True
        col1.prop(self,'dsPointOffsetX')
        col1.prop(self,'dsFrameOffset')
        col1.prop(self,'dsDistFromCursor')
        col1.prop(self,'dsIsAllowTextShadow')
        col1.use_property_split = True
        if self.dsIsAllowTextShadow:
            col1.prop(self,'dsShadowCol')
            col1 = where.column(align=True)
            col1.use_property_split = True
            row = col1.row(align=True)
            row.prop(self,'dsShadowOffset')
            col1 = col1.column()
            col1.prop(self,'dsShadowBlur')
        col1.prop(self,'dsIsDrawDebug')

    def draw_tabKeymaps(self, context, where):
        col0 = where.column()
        col0.separator()
        row = col0.row(align=True)
        row.label(text=bpy.app.translations.pgettext_iface("Node Editor"), icon='DOT')
        col1 = col0.column(align=True)
        kmNe = bpy.context.window_manager.keyconfigs.user.keymaps['Node Editor']
        list_getKmi = []
        for li in list_addonKeymaps:
            for kmiCon in kmNe.keymap_items:
                if (li.idname==kmiCon.idname)and(li.name==kmiCon.name):
                    list_getKmi.append(kmiCon)
        if kmNe.is_user_modified:
            row.label()
            row.context_pointer_set('keymap', kmNe)
            row.operator('preferences.keymap_restore', text=bpy.app.translations.pgettext_iface("Restore"))
        import rna_keymap_ui
        for li in sorted(set(list_getKmi), key=list_getKmi.index):
            col1.context_pointer_set('keymap', kmNe)
            rna_keymap_ui.draw_kmi([], context.window_manager.keyconfigs.user, kmNe, li, col1, 0)

    #Спасибо пользователю с ником "atticus-lv" за потрясную идею по компактной упаковке настроек.
    def draw(self, context):
        col0 = self.layout.column()
        col1 = col0.column(align=True)
        row0 = col1.row(align=True)
        #|11| Переключение вкладок через оператор создано, чтобы случайно не сменить вкладку при ведении зажатой мышки, кой есть особый соблазн с таким большим количеством "isColored"
        for li in [e for e in self.bl_rna.properties['vaUiTabs'].enum_items]:
            row0.operator(VoronoiAddonTabs.bl_idname, text=bpy.app.translations.pgettext_iface(li.name), depress=self.vaUiTabs==li.identifier).toTab = li.identifier
        #row0.prop(self, 'vaUiTabs', expand=True)
        match self.vaUiTabs:
            case 'SETTINGS':
                self.draw_tabSettings(context, col0)
            case 'DRAW':
                self.draw_tabDraw(context, col0)
            case 'KEYMAP':
                self.draw_tabKeymaps(context, col0)

class TranslationHelper():
    def __init__(self, data={}, lang=''):
        self.name = voronoiAddonName+lang
        self.translations_dict = dict()
        for src, src_trans in data.items():
            key = ('Operator', src)
            self.translations_dict.setdefault(lang, {})[key] = src_trans
            key = ('*', src)
            self.translations_dict.setdefault(lang, {})[key] = src_trans
    def register(self):
        try:
            bpy.app.translations.register(self.name, self.translations_dict)
        except:
            try:
                bpy.app.translations.unregister(self.name)
                bpy.app.translations.register(self.name, self.translations_dict)
            except:
                pass
    def unregister(self):
        bpy.app.translations.unregister(self.name)


dict_translateRU = {"Various utilities for nodes connecting, based on the distance field": "Разнообразные помогалочки для соединения нодов, основанные на поле расстояний",
                    "Virtual":                               "Виртуальный",
                    #Draw:
                    "Voronoi Linker settings:":              "Настройки Voronoi Linker:",
                    "Voronoi Preview settings:":             "Настройки Voronoi Preview:",
                    "Voronoi Mixer settings:":               "Настройки Voronoi Mixer:",
                    "Voronoi Hider settings:":               "Настройки Voronoi Hider:",
                    "Voronoi MassLinker settings:":          "Настройки Voronoi MassLinker:",
                    "Alternative uniform Color":             "Альтернативный постоянный цвет",
                    "Font File":                             "Файл шрифта",
                        "Only .ttf or .otf format":              "Только .ttf или .otf формат",
                    "Point offset X axis":                   "Смещение точки по оси X",
                    "Frame Size":                            "Размер рамки",
                    "Font Size":                             "Размер шрифта",
                    "Socket area":                           "Область сокета",
                    "Display Frame Style":                   "Стиль отображаемой рамки",
                        "Classic":                               "Классический",
                        "Simplified":                            "Упрощённый",
                        "Only text":                             "Только текст",
                    "Point size":                            "Размер точки ",
                    "Text distance from cursor":             "Расстояние до текста от курсора",
                    "Enable Text Shadow":                    "Включить тень текста",
                    "Shadow Offset":                         "Смещение тени",
                    "Shadow Blur":                           "Размытие тени",
                    "Always draw line for VoronoiLinker":    "Всегда рисовать линию для VoronoiLinker",
                    "Display debugging":                     "Отображать отладку",
                    #Settings:
                    "Allow crutch with collapsed node":      "Включить костыль со свёрнутыми нодами",
                    "Allow using classic Compositor Viewer": "Разрешить классический Viewer Композитора",
                    "Allow using classic GeoNodes Viewer":   "Разрешить классический Viewer Геометрических нодов",
                    "Socket color directly into a shader":   "Сокет цвета сразу в шейдер",
                    "Live Preview":                          "Предпросмотр в реальном времени",
                    "Select Previewed Node":                 "Выделять предпросматриваемый нод",
                    "Node Onion Colors":                     "Луковичные цвета нод",
                    "Trigger only on linked":                "Триггериться только на связанные",
                    "Topology connected highlighting":       "Подсветка топологических соединений",
                    "Save preview results":                  "Сохранять результаты предпросмотра",
                    "Include Fast Math Pie":                 "Подключить пирог быстрой математики",
                    "Empty placeholders":                    "Пустые заполнители",
                    "Activation trigger":                    "Триггер активации",
                        "At least one is a math socket":         "Хотя бы один из них математический сокет",
                        "Everyone is a math socket":             "Все из них математические сокеты",
                    "Pie Type":                              "Тип пирога",
                        "Speed":                                 "Скорость",
                        "Control":                               "Контроль",
                    "Display text for node":                 "Показывать текст для нода",
                        "Only name":                            "Только имя",
                        "Only label":                           "Только заголовок",
                        "Name and label":                       "Имя и заголовок",
                    "Toggle nodes on drag":                  "Переключать ноды при перетаскивании",
                    "Ignore existing links":                 "Игнорировать имеющиеся соединения"}


tuple_classes = (VoronoiAddonPrefs,VoronoiAddonTabs,
                 VoronoiLinker,
                 VoronoiPreviewer,
                 VoronoiMixer, VoronoiMixerMixer,VoronoiMixerPie, FastMathMain,FastMathPie,
                 VoronoiSwaper,
                 VoronoiHider,
                 VoronoiMassLinker,
                 #VoronoiDummy,
                 )
list_helpClasses = []
list_addonKeymaps = []
tuple_kmiDefs = ( (VoronoiLinker.bl_idname,    'RIGHTMOUSE', False, False, True,  {} ),
                  (VoronoiPreviewer.bl_idname, 'RIGHTMOUSE', True,  True,  False, {'isPlaceAnAnchor': True } ), #Якорь раньше, чтобы на вкладке "keymap" отображалось в правильном порядке.
                  (VoronoiPreviewer.bl_idname, 'LEFTMOUSE',  True,  True,  False, {'isPlaceAnAnchor': False} ),
                  (VoronoiMixer.bl_idname,     'RIGHTMOUSE', True,  False, True,  {} ),
                  (VoronoiSwaper.bl_idname,    'S',          False, False, True,  {'isAddMode': True} ), #Режим добавления раньше, чтобы на вкладке "keymap" отображалось в правильном порядке.
                  (VoronoiSwaper.bl_idname,    'S',          True,  False, False, {'isAddMode': False} ),
                  (VoronoiHider.bl_idname,     'E',          False, True,  False, {'isHideSocket': 0} ), #Не-сокет раньше, чтобы см. выше.
                  (VoronoiHider.bl_idname,     'E',          True,  False, False, {'isHideSocket': 1} ),
                  (VoronoiHider.bl_idname,     'E',          False, False, True,  {'isHideSocket': 2} ),
                  (VoronoiMassLinker.bl_idname,'RIGHTMOUSE', True,  True,  True,  {} ),
                  #(VoronoiDummy.bl_idname,    'D',          False, False, False, {} ),
                  )


def DisableKmis(): #Для повторных запусков скрипта. Радобает до первого 'Restore'.
    kmNe = bpy.context.window_manager.keyconfigs.user.keymaps['Node Editor']
    for ti, *ot in tuple_kmiDefs:
        for kmiCon in kmNe.keymap_items:
            if ti==kmiCon.idname:
                kmiCon.active = False #Это удаляет дубликаты. Хак?
                kmiCon.active = True #Вернуть обратно, если оригинал.
def register():
    for ti in tuple_classes:
        bpy.utils.register_class(ti)
    globalVars.newKeyMapNodeEditor = bpy.context.window_manager.keyconfigs.addon.keymaps.new(name="Node Editor", space_type='NODE_EDITOR')
    for blId, key, shift, ctrl, alt, dict_props in tuple_kmiDefs:
        kmi = globalVars.newKeyMapNodeEditor.keymap_items.new(idname=blId, type=key, value='PRESS', shift=shift, ctrl=ctrl, alt=alt)
        if dict_props:
            for ti in dict_props:
                setattr(kmi.properties, ti, dict_props[ti])
        list_addonKeymaps.append(kmi)
    #Переводы:
    list_helpClasses.append(TranslationHelper( dict_translateRU, 'ru_RU' ))
    for li in list_helpClasses:
        li.register()
def unregister():
    for ti in reversed(tuple_classes):
        bpy.utils.unregister_class(ti)
    for li in list_addonKeymaps:
        globalVars.newKeyMapNodeEditor.keymap_items.remove(kmi)
    list_addonKeymaps.clear()
    for li in list_helpClasses:
        li.unregister()


if __name__=="__main__":
    DisableKmis() #Кажется не важно в какой очерёдности вызывать, перед или после добавления хоткеев.
    register()

#Поскольку изначально завершение моих операторов было насильно запаяно проверкой "case 'RIGHTMOUSE'|'ESC':", иные хоткеи не отключали оператор.
#Я не знал как решить это правильным образом, поэтому придумал проверку "по факту". Оставлю этот код здесь:
    #    if event.value=='PRESS':
    #        self.dict_isAllToRelease[event.type] = True
    #    if (event.value=='RELEASE')and( self.dict_isAllToRelease.get(event.type, False) ):
    #        del self.dict_isAllToRelease[event.type]
    #    if (not self.dict_isAllToRelease)or(event.type=='ESC'):
    #
    #    self.dict_isAllToRelease = {event.type: True}
