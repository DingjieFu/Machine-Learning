import time
import random
import numpy as np
from scipy.io import loadmat
from sklearn.model_selection import train_test_split


# 加载数据
def loadData(trainPath, testPath):
    trainDict = loadmat(trainPath)
    testDict = loadmat(testPath)
    # print(f"总训练集:  样本数 {len(trainDict['X'])}  特征维度 {len(trainDict['X'][1])}")
    # print(f"总测试集:  样本数 {len(testDict['X'])}  特征维度 {len(testDict['X'][1])}")
    return trainDict['X'], trainDict['y'], testDict["X"]


def svmTrain_SMO(X, y, C, kernelFunction='linear', tol=1e-3, max_iter=5, **kargs):
    """
    利用简化版的SMO算法训练SVM
    （参考《机器学习实战》）

    输入：
    X, y为loadData函数的返回值
    C为惩罚系数
    kernelFunction表示核函数类型, 对于非线性核函数,也可直接输入核函数矩阵K
    tol为容错率
    max_iter为最大迭代次数

    输出：
    model['kernelFunction']为核函数类型
    model['X']为支持向量
    model['y']为对应的标签
    model['alpha']为对应的拉格朗日参数
    model['w'], model['b']为模型参数
    """

    start = time.perf_counter()

    m, n = X.shape
    X = np.mat(X)
    y = np.mat(y, dtype='float64')

    y[np.where(y == 0)] = -1

    alphas = np.mat(np.zeros((m, 1)))
    b = 0.0
    E = np.mat(np.zeros((m, 1)))
    iters = 0
    eta = 0.0
    L = 0.0
    H = 0.0

    if kernelFunction == 'linear':
        K = X*X.T
    elif kernelFunction == 'gaussian':
        K = kargs['K_matrix']
    else:
        print('Kernel Error')
        return None

    print('Training ...', end='')
    dots = 12
    while iters < max_iter:

        num_changed_alphas = 0
        for i in range(m):
            E[i] = b + \
                np.sum(np.multiply(np.multiply(alphas, y), K[:, i])) - y[i]

            if (y[i]*E[i] < -tol and alphas[i] < C) or (y[i]*E[i] > tol and alphas[i] > 0):
                j = np.random.randint(m)
                while j == i:
                    j = np.random.randint(m)

                E[j] = b + \
                    np.sum(np.multiply(np.multiply(alphas, y), K[:, j])) - y[j]

                alpha_i_old = alphas[i].copy()
                alpha_j_old = alphas[j].copy()

                if y[i] == y[j]:
                    L = max(0, alphas[j] + alphas[i] - C)
                    H = min(C, alphas[j] + alphas[i])
                else:
                    L = max(0, alphas[j] - alphas[i])
                    H = min(C, C + alphas[j] - alphas[i])

                if L == H:
                    continue

                eta = 2*K[i, j] - K[i, i] - K[j, j]
                if eta >= 0:
                    continue

                alphas[j] = alphas[j] - (y[j]*(E[i] - E[j]))/eta

                alphas[j] = min(H, alphas[j])
                alphas[j] = max(L, alphas[j])

                if abs(alphas[j] - alpha_j_old) < tol:
                    alphas[j] = alpha_j_old
                    continue

                alphas[i] = alphas[i] + y[i]*y[j]*(alpha_j_old - alphas[j])

                b1 = b - E[i]\
                    - y[i] * (alphas[i] - alpha_i_old) * K[i, j]\
                    - y[j] * (alphas[j] - alpha_j_old) * K[i, j]

                b2 = b - E[j]\
                    - y[i] * (alphas[i] - alpha_i_old) * K[i, j]\
                    - y[j] * (alphas[j] - alpha_j_old) * K[j, j]

                if (0 < alphas[i] and alphas[i] < C):
                    b = b1
                elif (0 < alphas[j] and alphas[j] < C):
                    b = b2
                else:
                    b = (b1+b2)/2.0

                num_changed_alphas = num_changed_alphas + 1

        if num_changed_alphas == 0:
            iters = iters + 1
        else:
            iters = 0

        print('.', end='')
        dots = dots + 1
        if dots > 78:
            dots = 0
            print()

    print('Done', end='')
    end = time.perf_counter()
    print('( '+str(end-start)+'s )')
    print()

    idx = np.where(alphas > 0)
    model = {'X': X[idx[0], :], 'y': y[idx], 'kernelFunction': str(kernelFunction),
             'b': b, 'alphas': alphas[idx], 'w': (np.multiply(alphas, y).T*X).T}
    return model


def gaussianKernelSub(x1, x2, sigma):
    """
    高斯核函数
    输入：
    x1, x2为向量
    sigma为高斯核参数
    """
    x1 = np.mat(x1).reshape(-1, 1)
    x2 = np.mat(x2).reshape(-1, 1)
    n = -(x1-x2).T*(x1-x2)/(2*sigma**2)
    return np.exp(n)


def gaussianKernel(X, sigma):
    """
    计算高斯核函数矩阵
    """
    start = time.perf_counter()
    print('GaussianKernel Computing ...', end='')
    m = X.shape[0]
    X = np.mat(X)
    K = np.mat(np.zeros((m, m)))
    dots = 280
    for i in range(m):
        if dots % 10 == 0:
            print('.', end='')
        dots = dots + 1
        if dots > 780:
            dots = 0
            print()
        for j in range(m):
            K[i, j] = gaussianKernelSub(X[i, :].T, X[j, :].T, sigma)
            K[j, i] = K[i, j].copy()

    print('Done', end='')
    end = time.perf_counter()
    print('( '+str(end-start)+'s )')
    print()
    return K


def svmPredict(model, X, *arg):
    """
    利用得到的model, 计算给定X的模型预测值
    输入：
    model为svmTrain_SMO返回值
    X为待预测数据
    sigma为训练参数
    """
    m = X.shape[0]
    p = np.mat(np.zeros((m, 1)))
    pred = np.mat(np.zeros((m, 1)))
    if model['kernelFunction'] == 'linear':
        p = X * model['w'] + model['b']
    else:
        for i in range(m):
            prediction = 0
            for j in range(model['X'].shape[0]):
                prediction += model['alphas'][:, j]*model['y'][:, j] *\
                    gaussianKernelSub(X[i, :].T, model['X'][j, :].T, *arg)
            p[i] = prediction + model['b']
    pred[np.where(p >= 0)] = 1
    pred[np.where(p < 0)] = 0
    return pred


def linearModel(X, y):
    for epoch in range(10):
        x_train, x_test, y_train, y_test = train_test_split(
            X, y, test_size=random.uniform(0.1, 0.3))
        print(f"实验训练集:  样本数 {len(x_train)}  特征维度 {len(x_train[1])}")
        print(f"实验测试集:  样本数 {len(x_test)}  特征维度 {len(x_test[1])}")
        model = svmTrain_SMO(x_train, y_train, C=1, max_iter=20)  # 模型训练
        # train_pre = svmPredict(model, x_train)  # 训练集
        # test_pre = svmPredict(model, x_test)  # 测试集
        # acc_train = accuracy(train_pre, y_train)
        # acc_test = accuracy(test_pre, y_test)
        # print(f"轮次:{epoch+1}, 训练集准确率{acc_train}, 测试集准确率{acc_test}")
        return model


# 预测精度
def accuracy(pre_y, true_y):
    acc = 1 - (abs(pre_y-true_y).sum())/len(true_y)
    return acc


def preTxt(Model, X):
    test_pre = svmPredict(Model, X).tolist()
    with open("test_labels.txt", mode="w") as f:
        for item in test_pre:
            f.write(str(int(item[0]))+"\n")


if __name__ == '__main__':
    train_path = 'PythonDeveloper/Machine_Learning/5_Support_Vector_Machine/task3/task3_train.mat'
    test_path = 'PythonDeveloper/Machine_Learning/5_Support_Vector_Machine/task3/task3_test.mat'
    train_X, train_y, test_X = loadData(train_path, test_path)
    model = linearModel(train_X, train_y)
    preTxt(model, test_X)
