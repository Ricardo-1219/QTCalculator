#ifndef CALCULATOR_H
#define CALCULATOR_H

#include <QMainWindow>
#include <QString>

QT_BEGIN_NAMESPACE
namespace Ui { class Calculator; }
QT_END_NAMESPACE

class QPushButton;
class QKeyEvent;

class Calculator : public QMainWindow
{
    Q_OBJECT

public:
    explicit Calculator(QWidget *parent = nullptr);
    ~Calculator();

protected:
    void keyPressEvent(QKeyEvent *event) override;   // 键盘输入

private slots:
    void onButtonClicked();     // 鼠标点击按键（所有按键共用）

private:
    //  四则运算类型
    enum class Op { None, Add, Sub, Mul, Div };

    Ui::Calculator *ui;

    //  ---------------- 计算器状态 ----------------
    double  m_firstOperand  = 0.0;      // 第一个操作数
    Op      m_pendingOp     = Op::None; // 待执行的运算符
    QString m_entry;                    // 当前正在输入的操作数（用字符串保存，便于处理小数点/退格）
    bool    m_startNewEntry = true;     // 下一次输入数字时是否开始新的操作数
    bool    m_showingResult = false;    // 当前显示的是否为计算结果
    bool    m_error         = false;    // 是否处于错误状态（如除以 0）

    //  ---------------- 内部处理 ----------------
    void    resetAll();                          // C：全部清除
    void    clearEntry();                        // CE：清除当前操作数
    void    inputDigit(const QString &digit);    // 输入数字
    void    inputDot();                          // 输入小数点
    void    backspace();                         // 退格
    void    toggleSign();                        // 正负号
    void    applyPercent();                      // %
    void    applyUnary(const QString &kind);     // 1/x、x²、√
    void    applyOperator(Op op);                // 四则运算符
    void    equals();                            // =
    void    showError(const QString &message);   // 显示错误并进入错误状态

    void    dispatch(const QString &token);      // 统一分发：鼠标与键盘都调用它
    double  currentValue() const;                // 当前操作数的数值
    bool    compute(double a, double b, Op op, double *result) const;  // 实际运算
    QString formatNumber(double value) const;    // 结果格式化
    QString opText(Op op) const;                 // 运算符显示文本
    void    updateDisplay();                     // 刷新显示区
    static QString buttonToken(const QString &text);   // 按键文本 -> 输入记号
};

#endif // CALCULATOR_H
