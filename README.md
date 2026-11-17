# reverie time

人人都是艺术家（Life is art），照片转化为油画风格

首次克隆后，将 `reverie/settings.example.py` 复制为 `reverie/settings.py`。使用 PostgreSQL 时，通过环境变量 `REVERIE_POSTGRES_USER` 和 `REVERIE_POSTGRES_PASSWORD` 配置账号。

运行 Photoshop 转换前，从 [Real Paint FX](https://graphicriver.net/item/animated-real-paint-fx-photoshop-addon-extension/23116581) 获取并安装预设，将流程所用的 JSX 放在 `data/action/Real-Paint-FX-subject.jsx`。记录 Photoshop 操作需要单独安装 [Adobe ScriptingListener](https://helpx.adobe.com/photoshop/desktop/app-integrations/install-scriptinglistener-plug-in.html)；JSXBIN 转换工具也在本地单独准备。
