#include "calculator.h"
#include "ui_calculator.h"

#include <QFile>
#include <QKeyEvent>
#include <QPushButton>

#include <cmath>

Calculator::Calculator(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::Calculator)
{
    ui->setupUi(this);

    //  载入样式表，统一界面外观
    QFile qss(":/style.qss");
    if (qss.open(QFile::ReadOnly | QFile::Text))
    {
        setStyleSheet(QString::fromUtf8(qss.readAll()));
        qss.close();
    }

    //  24 个按键全部连接到同一个槽：由按键上的文字决定要做什么，
    //  这样按键再多也只需要一个槽函数，便于后期维护。
    const QList<QPushButton *> buttons = findChildren<QPushButton *>();
    for (QPushButton *button : buttons)
        connect(button, &QPushButton::clicked, this, &Calculator::onButtonClicked);

    resetAll();
}

Calculator::~Calculator()
{
    delete ui;
}

// ---------------------------------------------------------------- 状态管理

//  C：清除全部状态，回到刚启动的样子
void Calculator::resetAll()
{
    m_firstOperand  = 0.0;
    m_pendingOp     = Op::None;
    m_entry         = "0";
    m_startNewEntry = true;
    m_showingResult = false;
    m_error         = false;

    ui->labExpression->clear();
    updateDisplay();
}

//  CE：只清除当前正在输入的操作数
void Calculator::clearEntry()
{
    m_error         = false;
    m_entry         = "0";
    m_startNewEntry = true;
    m_showingResult = false;
    updateDisplay();
}

// ---------------------------------------------------------------- 输入处理

void Calculator::inputDigit(const QString &digit)
{
    if (m_startNewEntry || m_showingResult)
    {
        //  结果之后或刚按过运算符，再输数字就是“新的一轮计算”
        m_entry         = digit;
        m_startNewEntry = false;
        m_showingResult = false;
    }
    else if (m_entry == "0")
    {
        m_entry = digit;              // 避免出现 007 这种前导 0
    }
    else if (m_entry == "-0")
    {
        m_entry = "-" + digit;
    }
    else
    {
        m_entry += digit;
    }
    updateDisplay();
}

void Calculator::inputDot()
{
    if (m_startNewEntry || m_showingResult)
    {
        m_entry         = "0.";       // 直接输入小数点时补前导 0
        m_startNewEntry = false;
        m_showingResult = false;
    }
    else if (!m_entry.contains('.'))
    {
        m_entry += ".";               // 同一个操作数只允许一个小数点
    }
    //  已含小数点时直接忽略，避免出现 1.2.3 这类非法输入
    updateDisplay();
}

void Calculator::backspace()
{
    if (m_startNewEntry || m_showingResult)
        return;                       // 新操作数或结果状态不响应退格

    m_entry.chop(1);
    if (m_entry.isEmpty() || m_entry == "-")
    {
        m_entry         = "0";
        m_startNewEntry = true;
    }
    updateDisplay();
}

void Calculator::toggleSign()
{
    if (m_entry == "0" || m_entry.isEmpty())
        return;

    if (m_entry.startsWith('-'))
        m_entry.remove(0, 1);
    else
        m_entry.prepend('-');

    m_showingResult = false;
    updateDisplay();
}

void Calculator::applyPercent()
{
    const double value = currentValue() / 100.0;
    m_entry         = formatNumber(value);
    m_startNewEntry = false;
    m_showingResult = false;
    updateDisplay();
}

void Calculator::applyUnary(const QString &kind)
{
    const double value = currentValue();
    double result = 0.0;

    if (kind == "recip")
    {
        if (value == 0.0) { showError(QString::fromUtf8("除数不能为 0")); return; }   // 1/0
        result = 1.0 / value;
    }
    else if (kind == "sqr")
    {
        result = value * value;
    }
    else // sqrt
    {
        if (value < 0.0) { showError(QString::fromUtf8("负数不能开平方")); return; }
        result = std::sqrt(value);
    }

    m_entry         = formatNumber(result);
    m_startNewEntry = false;
    m_showingResult = true;
    updateDisplay();
}

// ---------------------------------------------------------------- 四则运算

void Calculator::applyOperator(Op op)
{
    const double value = currentValue();

    if (m_pendingOp != Op::None && !m_startNewEntry)
    {
        //  连续运算：先把上一组运算算出来，再按新运算符继续
        double result = 0.0;
        if (!compute(m_firstOperand, value, m_pendingOp, &result))
            return;
        m_firstOperand = result;
        m_entry        = formatNumber(result);
    }
    else
    {
        //  第一个运算符，或“连续按运算符”时只替换运算符
        m_firstOperand = value;
    }

    m_pendingOp     = op;
    m_startNewEntry = true;
    m_showingResult = false;

    ui->labExpression->setText(formatNumber(m_firstOperand) + " " + opText(op));
    updateDisplay();
}

void Calculator::equals()
{
    if (m_pendingOp == Op::None)
    {
        //  没有待执行的运算符：把当前值当作结果（例如 5 = ）
        ui->labExpression->setText(m_entry + " =");
        m_showingResult = true;
        m_startNewEntry = true;
        return;
    }

    const double second = currentValue();
    double result = 0.0;
    if (!compute(m_firstOperand, second, m_pendingOp, &result))
        return;

    ui->labExpression->setText(formatNumber(m_firstOperand) + " " + opText(m_pendingOp)
                               + " " + formatNumber(second) + " =");

    m_entry         = formatNumber(result);
    m_firstOperand  = result;     // 结果可以继续参与下一次运算
    m_pendingOp     = Op::None;
    m_startNewEntry = true;
    m_showingResult = true;
    updateDisplay();
}

bool Calculator::compute(double a, double b, Op op, double *result) const
{
    switch (op)
    {
    case Op::Add: *result = a + b; break;
    case Op::Sub: *result = a - b; break;
    case Op::Mul: *result = a * b; break;
    case Op::Div:
        if (b == 0.0)
        {
            const_cast<Calculator *>(this)->showError(QString::fromUtf8("除数不能为 0"));
            return false;
        }
        *result = a / b;
        break;
    case Op::None:
    default:
        *result = b;
        break;
    }
    return true;
}

// ---------------------------------------------------------------- 分发与显示

//  统一分发：鼠标、键盘最终都调用这里，保证两种输入方式逻辑完全一致
void Calculator::dispatch(const QString &token)
{
    if (token.isEmpty())
        return;

    //  错误状态下只允许 C / CE 清除，避免继续用非法值计算
    if (m_error && token != "c" && token != "ce")
        return;

    if (token == "c")                                { resetAll();         return; }
    if (token == "ce")                               { clearEntry();       return; }
    if (token.size() == 1 && token[0].isDigit())     { inputDigit(token);  return; }
    if (token == ".")                                { inputDot();         return; }
    if (token == "+")                                { applyOperator(Op::Add); return; }
    if (token == "-")                                { applyOperator(Op::Sub); return; }
    if (token == "*")                                { applyOperator(Op::Mul); return; }
    if (token == "/")                                { applyOperator(Op::Div); return; }
    if (token == "=")                                { equals();           return; }
    if (token == "back")                             { backspace();        return; }
    if (token == "sign")                             { toggleSign();       return; }
    if (token == "percent")                          { applyPercent();     return; }
    if (token == "recip")                            { applyUnary("recip"); return; }
    if (token == "sqr")                              { applyUnary("sqr");   return; }
    if (token == "sqrt")                             { applyUnary("sqrt");  return; }
}

void Calculator::onButtonClicked()
{
    QPushButton *button = qobject_cast<QPushButton *>(sender());
    if (!button)
        return;
    dispatch(buttonToken(button->text()));
}

//  鼠标按键文字 -> 输入记号
QString Calculator::buttonToken(const QString &text)
{
    if (text.size() == 1 && text[0].isDigit())
        return text;

    if (text == ".")                            return ".";
    if (text == "+")                            return "+";
    if (text == "-" || text == QChar(0x2212))   return "-";     // −
    if (text == "*" || text == QChar(0x00D7))   return "*";     // ×
    if (text == "/" || text == QChar(0x00F7))   return "/";     // ÷
    if (text == "=")                            return "=";
    if (text == QChar(0x232B))                  return "back";  // ⌫
    if (text == "CE")                           return "ce";
    if (text == "C")                            return "c";
    if (text == QChar(0x00B1))                  return "sign";  // ±
    if (text == "%")                            return "percent";
    if (text == "1/x")                          return "recip";
    if (text == QString::fromUtf8("x²"))        return "sqr";
    if (text == QChar(0x221A))                  return "sqrt";  // √
    return QString();
}

//  键盘输入：把按键翻译成与鼠标完全相同的输入记号，再交给 dispatch
void Calculator::keyPressEvent(QKeyEvent *event)
{
    const QString text = event->text();
    QString token;

    if (text.size() == 1 && text[0].isDigit())
        token = text;
    else if (text == ".")
        token = ".";
    else if (text == "+")
        token = "+";
    else if (text == "-")
        token = "-";
    else if (text == "*" || text == "x" || text == "X")
        token = "*";
    else if (text == "/")
        token = "/";
    else if (text == "%")
        token = "percent";

    if (token.isEmpty())
    {
        switch (event->key())
        {
        case Qt::Key_Enter:
        case Qt::Key_Return:
        case Qt::Key_Equal:      token = "=";    break;
        case Qt::Key_Backspace:  token = "back"; break;
        case Qt::Key_Escape:     token = "c";    break;
        case Qt::Key_Delete:     token = "ce";   break;
        default: break;
        }
    }

    if (!token.isEmpty())
        dispatch(token);          // 与鼠标走同一条处理路径
    else
        QMainWindow::keyPressEvent(event);
}

// ---------------------------------------------------------------- 辅助函数

double Calculator::currentValue() const
{
    bool ok = false;
    const double value = m_entry.toDouble(&ok);
    return ok ? value : 0.0;
}

QString Calculator::formatNumber(double value) const
{
    if (!std::isfinite(value))
        return QString("0");

    QString text = QString::number(value, 'g', 12);   // 最多 12 位有效数字

    //  'g' 对整数会输出 "3"，对 0.1+0.2 会输出 "0.3"；这里再处理一下 "-0"
    if (text == "-0")
        text = "0";
    return text;
}

QString Calculator::opText(Op op) const
{
    switch (op)
    {
    case Op::Add: return "+";
    case Op::Sub: return QString(QChar(0x2212));   // −
    case Op::Mul: return QString(QChar(0x00D7));   // ×
    case Op::Div: return QString(QChar(0x00F7));   // ÷
    case Op::None:
    default:      return QString();
    }
}

void Calculator::updateDisplay()
{
    ui->editDisplay->setText(m_entry.isEmpty() ? QString("0") : m_entry);
}

void Calculator::showError(const QString &message)
{
    m_error         = true;
    m_entry         = message;
    m_firstOperand  = 0.0;
    m_pendingOp     = Op::None;
    m_startNewEntry = true;
    m_showingResult = true;
    ui->labExpression->clear();
    updateDisplay();
}
