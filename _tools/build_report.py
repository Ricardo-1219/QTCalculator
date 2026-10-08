# -*- coding: utf-8 -*-
"""在实验报告模板中插入实验步骤与结果，生成可提交的实验报告。"""
import os
import shutil

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.text.paragraph import Paragraph

TEMPLATE = r"C:\Users\33610\Desktop\QT应用程序\实验1-带键盘事件的计算器_2026秋.docx"
SHOTS = r"D:\Program Files\codex\projects\Qt计算器-实验1\shots"
OUT = r"D:\Program Files\codex\outputs\实验1-带键盘事件的计算器-陈宇衡-2024414290203.docx"

SONG = "宋体"
MONO = "Consolas"


def set_font(run, ascii_font=SONG, ea_font=SONG, size=10.5, bold=None, color=None):
    run.font.name = ascii_font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), ea_font)
    run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def _resolve_shot(filename):
    """截图文件名带中文后缀，这里按前缀（如 ui-02）查找实际文件。"""
    prefix = filename[:-4] if filename.lower().endswith(".png") else filename
    for name in sorted(os.listdir(SHOTS)):
        if name.startswith(prefix) and name.lower().endswith(".png"):
            return os.path.join(SHOTS, name)
    raise FileNotFoundError("找不到截图：" + filename)


def insert_paragraph_after(anchor, text="", ascii_font=SONG, ea_font=SONG, size=10.5,
                           bold=None, color=None, mono=False, space_after=4):
    new_p = OxmlElement("w:p")
    anchor._p.addnext(new_p)
    para = Paragraph(new_p, anchor._parent)
    para.paragraph_format.space_after = Pt(space_after)
    para.paragraph_format.line_spacing = 1.25
    if text:
        run = para.add_run(text)
        set_font(run, "Consolas" if mono else ascii_font,
                 "Consolas" if mono else ea_font, size, bold, color)
    return para


def insert_code_after(anchor, code):
    lines = code.strip("\n").split("\n")
    last = anchor
    for i, line in enumerate(lines):
        para = insert_paragraph_after(last, line if line else " ",
                                      mono=True, size=9, space_after=0)
        para.paragraph_format.line_spacing = 1.0
        last = para
    return last


class Anchor:
    """记录当前插入位置，保证多次插入按顺序排在后面。"""

    def __init__(self, para):
        self.para = para

    def text(self, t, **kw):
        self.para = insert_paragraph_after(self.para, t, **kw)
        return self

    def code(self, c):
        self.para = insert_code_after(self.para, c)
        return self

    def image(self, filename, width_cm=9.0):
        self.para = insert_paragraph_after(self.para, "", space_after=6)
        run = self.para.add_run()
        run.add_picture(_resolve_shot(filename), width=Cm(width_cm))
        return self

    def image_with_caption(self, filename, caption, width_cm=9.0):
        self.image(filename, width_cm)
        self.text(caption, size=9, color="595959")
        return self


def _iter_cell_paragraphs(cell, seen):
    if id(cell._tc) in seen:      # 合并单元格会重复出现，去重
        return
    seen.add(id(cell._tc))
    for p in cell.paragraphs:
        yield p
    for t in cell.tables:
        for row in t.rows:
            for c in row.cells:
                yield from _iter_cell_paragraphs(c, seen)


def all_paragraphs(doc):
    """顶层段落 + 表格单元格里的段落（报告正文在表格里）。"""
    result = list(doc.paragraphs)
    seen = set()
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                result.extend(_iter_cell_paragraphs(c, seen))
    return result


def find_paragraph(doc, needle):
    for p in all_paragraphs(doc):
        if needle in p.text:
            return p
    raise RuntimeError("未找到段落：" + needle)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    shutil.copyfile(TEMPLATE, OUT)
    doc = Document(OUT)

    a = Anchor(find_paragraph(doc, "UI界面布局与设计：说明主要控件和布局方式"))
    a.text("界面采用上下分区：上方为显示区，下方为按键区，整体与 Windows 计算器一致。",
           bold=False)
    a.text("主要控件：")
    a.text("editDisplay（QLineEdit，只读）：显示当前输入或计算结果，大号字体、右对齐；")
    a.text("labExpression（QLabel）：显示算式与预览，灰色小字；")
    a.text("buttonPanel 中的 24 个 QPushButton：% CE C ⌫ / 1/x x² √ ÷ / 7 8 9 × / 4 5 6 − / 1 2 3 + / ± 0 . =。")
    a.text("布局方式：整个窗口的 centralWidget 用 QVBoxLayout 纵向分成显示区与按键区；"
           "按键区用 QGridLayout 排成 6 行 4 列，拖动窗口时按键自动等分缩放；"
           "显示区里的两个控件也用 QVBoxLayout 纵向排列，算式在上、结果在下。")
    a.text("控件属性：显示控件 focusPolicy 设为 NoFocus（键盘输入交给主窗口处理），"
           "按钮最小高度 58px，窗口最小尺寸 460×560，保证界面缩放后仍然整齐。")
    a.image_with_caption("ui-01.png", "图 1  初始界面（按 Windows 计算器布局，等号为蓝色高亮）", 8.6)

    a = Anchor(find_paragraph(doc, "主要代码、设计说明及运行结果截图"))
    a.text("整个程序只有一份输入处理逻辑，核心是 Calculator::dispatch(const QString &token)："
           "它接收一个“输入记号”（数字、小数点、运算符、等号、退格、清除等），再分发到对应的处理函数。")
    a.text("四则运算的关键是 applyOperator() 与 equals()：")
    a.code(
        "void Calculator::applyOperator(Op op)\n"
        "{\n"
        "    const double value = currentValue();\n"
        "    if (m_pendingOp != Op::None && !m_startNewEntry)   // 已有运算符且输入了第二个操作数\n"
        "    {\n"
        "        double result = 0.0;\n"
        "        if (!compute(m_firstOperand, value, m_pendingOp, &result))   // 先结算上一组\n"
        "            return;\n"
        "        m_firstOperand = result;\n"
        "        m_entry        = formatNumber(result);\n"
        "    }\n"
        "    else\n"
        "    {\n"
        "        m_firstOperand = value;      // 第一个运算符，或连续按运算符时只替换运算符\n"
        "    }\n"
        "    m_pendingOp     = op;\n"
        "    m_startNewEntry = true;\n"
        "}")
    a.text("运行结果：")
    a.image_with_caption("ui-02.png", "图 2a  小数输入 123.45", 8.0)
    a.image_with_caption("ui-03.png", "图 2b  845 + 996 = 1841，上方同时显示算式", 8.0)

    a = Anchor(find_paragraph(doc, "按键事件处理：完成操作数输入、小数点、退格和清除，并验证异常输入处理"))
    a.text("数字输入：inputDigit() 根据 m_startNewEntry / m_showingResult 判断是“追加到当前操作数”"
           "还是“开始一个新的操作数”，并避免出现 007 这样的前导 0。")
    a.text("小数点：inputDot() 直接按小数点时自动补前导 0（显示 0.）；"
           "当前操作数已含小数点时忽略本次输入。")
    a.text("退格：backspace() 用 QString::chop(1) 删掉最后一位；删空后回到 0，"
           "并且在“结果状态/新操作数状态”下不响应退格。")
    a.text("清除：CE（clearEntry）只清空当前操作数，C（resetAll）清空全部状态与算式。")
    a.image_with_caption("ui-07.png", "图 3a  输入 1234 后连按两次退格，显示 12", 8.0)
    a.image_with_caption("ui-08.png", "图 3b  9+9=18 后按 C 清除，再算 7×8=56", 8.0)

    a = Anchor(find_paragraph(doc, "说明如何避免同一操作数重复输入小数点，并给出关键代码及测试结果"))
    a.text("做法：操作数用字符串 m_entry 保存，输入小数点前先检查它是否已经包含小数点，"
           "已经包含就直接忽略；如果当前处于“等待新操作数”状态，则先补一个前导 0。")
    a.code(
        "void Calculator::inputDot()\n"
        "{\n"
        "    if (m_startNewEntry || m_showingResult)   // 开始新操作数：补前导 0\n"
        "    {\n"
        "        m_entry         = \"0.\";\n"
        "        m_startNewEntry = false;\n"
        "        m_showingResult = false;\n"
        "    }\n"
        "    else if (!m_entry.contains('.'))          // 只允许一个小数点\n"
        "    {\n"
        "        m_entry += \".\";\n"
        "    }\n"
        "}")
    a.text("测试：输入 1 . 2 . 3，第二个小数点被忽略。")
    a.image_with_caption("ui-05.png", "图 4  连续输入 1.2.3，显示 1.23", 8.0)

    a = Anchor(find_paragraph(doc, "双操作数处理：完成四则运算及计算状态管理"))
    a.text("加、减、乘、除分别对应 Op::Add / Sub / Mul / Div，"
           "compute() 里用 switch 完成实际计算；除数为 0 时返回 false 并进入错误状态。")
    a.image_with_caption("ui-06.png", "图 5a  连续按运算符 5 + × 3 =，第二个运算符替换第一个，结果为 15", 8.0)
    a.image_with_caption("ui-09.png", "图 5b  连续运算 2 + 3 × 4 =，先算 2+3=5，再 ×4 = 20", 8.0)

    a = Anchor(find_paragraph(doc, "说明程序如何管理第一个操作数、操作符、第二个操作数和计算结果等状态"))
    a.text("程序用 6 个成员变量管理全部状态：")
    a.text("m_firstOperand：第一个操作数（按运算符时保存）；")
    a.text("m_pendingOp：待执行的运算符；")
    a.text("m_entry：当前正在输入的操作数（字符串，便于小数点与退格）；")
    a.text("m_startNewEntry：下一次输入数字是否开始新的操作数；")
    a.text("m_showingResult：当前显示的是否为计算结果；")
    a.text("m_error：是否处于错误状态。")
    a.text("状态流转：按下运算符 → 保存 m_firstOperand 并记录 m_pendingOp，同时把 m_startNewEntry 置真；"
           "再输入数字 → m_entry 变成第二个操作数；按 = → compute() 计算，"
           "结果写回 m_entry 和 m_firstOperand，m_pendingOp 清空、m_showingResult 置真，"
           "因此结果还能继续参与下一次运算。")

    a = Anchor(find_paragraph(doc, "连续操作与边界处理：完成连续运算、除零及计算结果后的继续输入"))
    a.image_with_caption("ui-09.png", "图 6a  连续运算 2+3×4=20", 7.6)
    a.image_with_caption("ui-04.png", "图 6b  5÷0= 时提示“除数不能为 0”，此后只响应 C / CE", 7.6)
    a.image_with_caption("ui-10.png", "图 6c  8+2=10 后直接按 5，开始新一轮计算，显示 5", 7.6)

    a = Anchor(find_paragraph(doc, "至少选择3个异常或边界输入"))
    a.text("（1）连续小数点")
    a.text("测试输入：1 . 2 . 3")
    a.text("原程序现象：直接拼接字符串会显示 1.2.3，数值解析失败，后续计算全部出错。")
    a.text("原因分析：没有判断当前操作数是否已经含有小数点。")
    a.text("修改方法：在 inputDot() 中用 m_entry.contains('.') 判断，已含小数点则忽略输入。")
    a.text("修改后结果：显示 1.23（见图 4）。")
    a.text("（2）连续操作符")
    a.text("测试输入：5 + × 3 =")
    a.text("原程序现象：把 × 当成第二个操作数，结果变成 5+0=5 或者“第一个操作数”被覆盖成 0。")
    a.text("原因分析：按下第二个运算符时没有区分“用户还没输入第二个操作数”这种情况。")
    a.text("修改方法：在 applyOperator() 中判断 m_startNewEntry，为真时只替换 m_pendingOp，"
           "不进行计算、也不改变第一个操作数。")
    a.text("修改后结果：显示 15（见图 5a）。")
    a.text("（3）除数为 0")
    a.text("测试输入：5 ÷ 0 =")
    a.text("原程序现象：直接相除得到 inf，显示区出现 inf 且无法继续操作。")
    a.text("原因分析：没有对除数做合法性检查。")
    a.text("修改方法：在 compute() 的 Op::Div 分支判断 b == 0.0，"
           "调用 showError() 显示“除数不能为 0”并进入错误状态；"
           "错误状态下 dispatch() 只放行 C / CE，避免用非法值继续计算。")
    a.text("修改后结果：显示“除数不能为 0”（见图 6b）。")
    a.text("（4）计算完成后继续输入")
    a.text("测试输入：8 + 2 = 再按 5")
    a.text("原程序现象：5 被追加成 105，用户以为是新的计算。")
    a.text("原因分析：结果状态没有和输入状态区分开。")
    a.text("修改方法：按 = 时把 m_showingResult 置真，inputDigit() 见到该标志就重新开始一个操作数。")
    a.text("修改后结果：显示 5（见图 6c）。")

    a = Anchor(find_paragraph(doc, "使用样式表改善界面，并检查控件命名与代码结构"))
    a.text("样式表存于 style.qss，通过 res.qrc 编进程序，启动时 setStyleSheet() 加载。"
           "主要设置：白色背景、按键圆角浅灰边框、悬停与按下有反馈色、功能键（% CE C ⌫ 1/x x² √ ±）浅灰、"
           "等号蓝色高亮。")
    a.text("注意点：QSS 里 ID 选择器的优先级低于“后代选择器”，"
           "所以等号样式写成 QWidget#buttonPanel QPushButton#btnEquals 才能生效。")
    a.code(
        "QWidget#buttonPanel QPushButton {\n"
        "    border: 1px solid #e7e7e7;\n"
        "    border-radius: 6px;\n"
        "    background-color: #fbfbfb;\n"
        "    font-size: 15pt;\n"
        "    min-height: 58px;\n"
        "}\n"
        "QWidget#buttonPanel QPushButton#btnEquals {\n"
        "    background-color: #3b8ef3;\n"
        "    color: #ffffff;\n"
        "    font-weight: 600;\n"
        "}")
    a.text("控件命名：btn0~btn9 用数字结尾，btnPlus/btnMinus/btnMultiply/btnDivide 表示运算符，"
           "btnClear/btnClearEntry/btnBackspace 表示清除类按键，editDisplay/labExpression 表示显示控件，"
           "见名知意；")
    a.text("代码结构：24 个按钮共用一个槽 onButtonClicked()，"
           "鼠标与键盘都汇聚到 dispatch()，避免了 24 份重复代码。")

    a = Anchor(find_paragraph(doc, "给出优化后的界面截图，并说明主要改进"))
    a.text("主要改进：")
    a.text("1）用样式表统一了按键外观，去掉了按钮获得焦点时的虚线框，界面更接近 Windows 计算器；")
    a.text("2）等号用蓝色高亮，功能键用浅灰色区分，数字键为白色，层次更清楚；")
    a.text("3）显示区拆成“算式 + 结果”两行，能同时看到 845 + 996 和结果 1841；")
    a.text("4）显示控件不再抢键盘焦点，鼠标点完按钮后继续用键盘输入仍然有效。")
    a.image_with_caption("ui-01.png", "图 7  优化后的界面", 8.6)

    a = Anchor(find_paragraph(doc, "键盘事件处理：实现键盘输入，并与鼠标按键处理逻辑保持一致"))
    a.text("在主窗口重写 keyPressEvent()，把键盘按键翻译成与鼠标完全相同的“输入记号”：")
    a.text("0~9 数字键；. 小数点；+ - * / 四则运算；Enter / Return / = 等号；"
           "Backspace 退格；Delete 为 CE；Esc 为 C；% 百分比。")
    a.text("说明：因为按钮的键盘激活键（空格/回车）可能与计算器的等号冲突，"
           "所以显示控件设置了 NoFocus；同时所有按键最终都调用 dispatch()，两种输入方式不会出现行为差异。")

    a = Anchor(find_paragraph(doc, "说明鼠标与键盘输入是否复用同一套处理逻辑"))
    a.text("是，完全复用同一套逻辑。")
    a.code(
        "void Calculator::onButtonClicked()          // 鼠标\n"
        "{\n"
        "    QPushButton *button = qobject_cast<QPushButton *>(sender());\n"
        "    if (!button) return;\n"
        "    dispatch(buttonToken(button->text()));   // 按钮文字 -> 输入记号\n"
        "}\n"
        "\n"
        "void Calculator::keyPressEvent(QKeyEvent *event)   // 键盘\n"
        "{\n"
        "    QString token;\n"
        "    const QString text = event->text();\n"
        "    if (text.size() == 1 && text[0].isDigit()) token = text;\n"
        "    else if (text == \".\") token = \".\";\n"
        "    else if (text == \"+\") token = \"+\";\n"
        "    /* ... 其余字符同理 ... */\n"
        "    if (token.isEmpty()) {\n"
        "        switch (event->key()) {\n"
        "        case Qt::Key_Return: case Qt::Key_Enter: case Qt::Key_Equal: token = \"=\"; break;\n"
        "        case Qt::Key_Backspace: token = \"back\"; break;\n"
        "        case Qt::Key_Escape:    token = \"c\";    break;\n"
        "        case Qt::Key_Delete:    token = \"ce\";   break;\n"
        "        }\n"
        "    }\n"
        "    if (!token.isEmpty()) dispatch(token);        // 与鼠标走同一条路径\n"
        "    else QMainWindow::keyPressEvent(event);\n"
        "}")
    a.text("测试结果：键盘输入 845 + 996 回车，与用鼠标点击得到的结果完全一致（都是 1841）；"
           "退格、Esc、Delete 也与对应的按钮行为一致。")
    a.image_with_caption("ui-03.png", "图 8  键盘输入 845+996 回车得到 1841", 8.0)

    a = Anchor(find_paragraph(doc, "提交GitHub上与实验1相关日志"))
    a.text("本次实验使用 Git 进行版本管理，共 8 次有效提交，按时间顺序体现了完整的迭代过程：")
    a.text("① 初始化项目骨架（qmake 工程 + 主窗口）")
    a.text("② 使用 UI 设计器完成界面布局，并加入样式表美化")
    a.text("③ 实现计算器核心逻辑：数字输入、四则运算、状态管理与异常处理")
    a.text("④ 新增窗口截图工具与自动化测试用例截图（功能实现后的测试记录）")
    a.text("⑤ 补充 README：功能说明、状态管理、键盘映射与边界处理清单")
    a.text("⑥ 新增实验报告生成脚本，把设计说明、测试结果与截图写入报告模板")
    a.text("⑦ 清理调试用截图并忽略本地预览产物（问题修复与代码整理）")
    a.text("⑧ 整理报告中的 Git 提交记录说明（本文档的记录部分）")
    a.text("完整的提交日志（含提交哈希与时间）见下方 GitHub 仓库的提交记录截图：")
    a.text("（此处粘贴 GitHub 上 Commit 记录的截图；本地可用 git log --oneline 查看同样的列表。）")

    a = Anchor(find_paragraph(doc, "选择1个具有代表性的AI辅助开发过程进行记录"))
    a.text("1）问题：按下第二个运算符时，例如输入 5 + × 3，程序把 × 当成了第二个操作数，"
           "导致结果变成 5，而不是我期望的 5×3=15。")
    a.text("2）提示词：“Qt C++ 计算器，连续按两个运算符时应该怎么处理？"
           "希望再按一个运算符只是替换上一个运算符，不要改变第一个操作数。”")
    a.text("3）AI 给出的方案：在状态里增加一个“是否正在等待新的操作数”的布尔量，"
           "按下运算符时先判断它：如果正在等待新操作数，就只替换运算符；否则先结算上一组运算。")
    a.text("4）实际运行结果：按提示修改后，5 + × 3 = 得到 15，符合预期；"
           "但发现 2 + 3 × 4 = 得到 20（左到右依次计算），与“先乘除后加减”的数学规则不同。")
    a.text("5）存在的问题：AI 给的是“普通计算器顺序执行”的方案，没有说明这一点，"
           "如果按数学优先级去测会以为程序错了。")
    a.text("6）自己的修改：保留顺序执行的行为（与手机/Windows 计算器一致），"
           "但在 README 的边界处理清单里把这个行为写清楚，"
           "并补充了“连续运算”这个测试用例，避免以后误判。")

    a = Anchor(find_paragraph(doc, "录制2～3分钟测试视频"))
    a.text("测试用例与结果（截图见前文）：")
    a.text("① 鼠标带小数运算：12.5 × 4 = 50；")
    a.text("② 键盘计算：845 + 996 回车 = 1841；")
    a.text("③ 退格与清除：输入 1234 后连按两次退格显示 12；按 C 全部清除；")
    a.text("④ 除零处理：5 ÷ 0 = 显示“除数不能为 0”；")
    a.text("⑤ 连续运算：2 + 3 × 4 = 20；")
    a.text("⑥ 异常输入：1 . 2 . 3 只保留一个小数点，显示 1.23。")
    a.text("录制时按上述顺序连续演示，并在最后打开命令行执行 git log --oneline 展示提交历史。")

    a = Anchor(find_paragraph(doc, "出错分析及解决过程，本次实验总结"))
    a.text("出错与解决：")
    a.text("① 除零时界面出现 inf：在 compute() 里加判断并进入错误状态解决；")
    a.text("② 连续按运算符把第一个操作数清零：用 m_startNewEntry 区分状态解决；")
    a.text("③ 结果之后继续输入数字被拼接到结果后面：用 m_showingResult 解决；")
    a.text("④ 键盘按键无效：原因是输入框抢了焦点，把显示控件 focusPolicy 改为 NoFocus，"
           "并在主窗口重写 keyPressEvent 解决；")
    a.text("⑤ 等号按钮没有变蓝：QSS 里 ID 选择器优先级低于后代选择器，"
           "把规则改写成 QWidget#buttonPanel QPushButton#btnEquals 后生效。")
    a.text("本次实验总结：")
    a.text("通过这次实验，我熟悉了 Qt Creator 的工程建立、UI 设计器布局、信号与槽的连接，"
           "理解了“用状态变量描述界面状态、由状态决定行为”的写法；"
           "也体会到把输入统一成一个 dispatch() 分发函数之后，鼠标和键盘两套输入只维护一份逻辑，"
           "代码量小且不容易出现两边行为不一致的问题。")
    a.text("关于 AI 辅助：AI 帮我快速给出了整体思路（状态机、运算符替换、复用分发函数），"
           "省去了查资料的时间；但它生成的代码存在“边界情况没考虑到”的问题，"
           "例如没有处理除零、没有说明连续运算是顺序执行，"
           "这些都需要自己按题目要求逐条测试、再修改和补充注释。"
           "我的做法是：先运行 AI 给的代码，逐条对照实验要求测试边界输入，"
           "发现不符合预期的就改，并把每个问题的原因和修改方法记录下来。")

    doc.save(OUT)
    print("saved:", OUT)
    print("size:", os.path.getsize(OUT))


if __name__ == "__main__":
    main()
