我想做一个微信小程序，用户上传一张照片，我处理后，用户下载。

主页面有三个引导栏：上传照片，我的照片（保存90天），我的信息（账号、剩余张数、进行充值）

# 搭建微信小程序照片处理系统

你想要开发一个微信小程序，核心流程是用户上传照片后由后台完成处理，处理完毕后用户可下载；小程序主页面通过底部 tabBar 实现三个核心功能入口——上传照片、我的照片（存储用户照片且有效期90天）、我的信息（展示账号信息、剩余可处理照片张数，支持充值）。我会为你提供**完整的小程序前端核心代码**（原生微信小程序），并说明后端关键逻辑和注意事项，帮你快速搭建基础框架。

### 一、整体架构说明

| 模块     | 技术选型/实现方式                                            |
| -------- | ------------------------------------------------------------ |
| 前端     | 微信小程序原生开发（WXML/WXSS/JS/JSON），底部 tabBar 实现三个核心入口 |
| 后端     | 推荐 Node.js（Express/Koa）/Java SpringBoot，负责照片处理、用户信息/存储管理 |
| 照片存储 | 微信云存储/阿里云 OSS（配置 90 天自动过期规则）              |
| 用户认证 | 基于微信 openid 标识用户（无需注册，一键登录）               |
| 充值功能 | 对接微信支付（需小程序认证、商户号）                         |
| 照片处理 | 后端调用图像处理接口（如 OpenCV/PS 脚本/第三方 AI 抠图接口） |

### 二、核心配置与页面代码

#### 1. 全局配置（app.json）：配置 tabBar 与页面路由

```JSON
{
  "pages": [
    "pages/upload/upload",    // 上传照片页
    "pages/photos/photos",    // 我的照片页
    "pages/profile/profile"   // 我的信息页
  ],
  "window": {
    "backgroundTextStyle": "light",
    "navigationBarBackgroundColor": "#fff",
    "navigationBarTitleText": "照片处理工具",
    "navigationBarTextStyle": "black"
  },
  "tabBar": {
    "color": "#666",
    "selectedColor": "#0088ff",
    "backgroundColor": "#f9f9f9",
    "borderStyle": "black",
    "list": [
      {
        "pagePath": "pages/upload/upload",
        "text": "上传照片",
        "iconPath": "/images/upload.png",    // 需自行准备图标
        "selectedIconPath": "/images/upload-active.png"
      },
      {
        "pagePath": "pages/photos/photos",
        "text": "我的照片",
        "iconPath": "/images/photos.png",
        "selectedIconPath": "/images/photos-active.png"
      },
      {
        "pagePath": "pages/profile/profile",
        "text": "我的信息",
        "iconPath": "/images/profile.png",
        "selectedIconPath": "/images/profile-active.png"
      }
    ]
  },
  "sitemapLocation": "sitemap.json",
  "permission": {
    "scope.writePhotosAlbum": {
      "desc": "需要获取保存图片到相册的权限，以便你下载处理后的照片"
    }
  }
}
```

#### 2. 上传照片页面（pages/upload/upload）

##### 2.1 WXML（upload.wxml）

```XML
<view class="container">
  <!-- 照片选择区域 -->
  <view class="upload-area" bindtap="chooseImage">
    <image wx:if="{{tempFilePath}}" src="{{tempFilePath}}" mode="aspectFill"></image>
    <view wx:else class="upload-placeholder">
      <icon type="image" size="60" color="#999"></icon>
      <text>点击选择照片</text>
    </view>
  </view>

  <!-- 上传按钮 -->
  <button 
    class="upload-btn" 
    wx:if="{{tempFilePath && !uploading}}" 
    bindtap="uploadImage"
    disabled="{{!tempFilePath}}"
  >
    上传并处理照片
  </button>

  <!-- 上传中状态 -->
  <view wx:if="{{uploading}}" class="loading">
    <van-loading type="spinner" size="20px">处理中...</van-loading>
  </view>

  <!-- 处理完成提示 -->
  <view wx:if="{{processDone}}" class="done-tip">
    <text>处理完成！可前往【我的照片】下载</text>
    <button bindtap="toPhotos">前往我的照片</button>
  </view>
</view>
```

注：`van-loading` 是 vant-weapp 组件（需安装：`npm i @vant/weapp`），也可替换为微信原生 loading。

##### 2.2 WXSS（upload.wxss）

```CSS
.container {
  padding: 20rpx;
  min-height: 100vh;
  background-color: #f5f5f5;
}

.upload-area {
  width: 100%;
  height: 400rpx;
  border: 2rpx dashed #ccc;
  border-radius: 10rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 30rpx;
}

.upload-area image {
  width: 100%;
  height: 100%;
  border-radius: 8rpx;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #999;
}

.upload-placeholder text {
  margin-top: 20rpx;
  font-size: 28rpx;
}

.upload-btn {
  background-color: #0088ff;
  color: #fff;
  border-radius: 8rpx;
  height: 80rpx;
  line-height: 80rpx;
  font-size: 32rpx;
}

.loading, .done-tip {
  margin-top: 30rpx;
  text-align: center;
  font-size: 28rpx;
  color: #666;
}

.done-tip button {
  margin-top: 20rpx;
  background-color: #fff;
  color: #0088ff;
  border: 1rpx solid #0088ff;
}
```

##### 2.3 JS（upload.js）：核心上传逻辑

```JavaScript
Page({
  data: {
    tempFilePath: '',   // 本地临时照片路径
    uploading: false,   // 上传/处理中状态
    processDone: false  // 处理完成状态
  },

  // 选择照片（微信小程序本地选择）
  chooseImage() {
    wx.chooseImage({
      count: 1,  // 仅允许选1张
      sizeType: ['original', 'compressed'],  // 原图/压缩图
      sourceType: ['album', 'camera'],       // 相册/相机
      success: (res) => {
        // 获取临时文件路径
        this.setData({
          tempFilePath: res.tempFilePaths[0],
          processDone: false
        });
      },
      fail: (err) => {
        wx.showToast({
          title: '选择照片失败',
          icon: 'none'
        });
        console.error('选择照片失败：', err);
      }
    });
  },

  // 上传照片到后端
  uploadImage() {
    if (!this.data.tempFilePath) return;

    this.setData({ uploading: true });

    // 1. 先获取用户openid（需后端接口支持，提前完成登录）
    const openid = wx.getStorageSync('openid') || '';
    if (!openid) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      this.setData({ uploading: false });
      return;
    }

    // 2. 上传文件到后端
    wx.uploadFile({
      url: 'https://你的后端域名/api/upload',  // 替换为实际后端接口
      filePath: this.data.tempFilePath,
      name: 'photo',  // 后端接收的文件字段名
      formData: {
        openid: openid,  // 传递用户标识
        timestamp: Date.now()  // 时间戳防重
      },
      success: (res) => {
        // 后端返回处理结果（如照片ID、处理状态）
        const result = JSON.parse(res.data);
        if (result.code === 200) {
          this.setData({
            uploading: false,
            processDone: true
          });
          wx.showToast({ title: '上传成功，处理中' });
        } else {
          wx.showToast({ title: result.msg || '处理失败', icon: 'none' });
          this.setData({ uploading: false });
        }
      },
      fail: (err) => {
        wx.showToast({ title: '上传失败', icon: 'none' });
        this.setData({ uploading: false });
        console.error('上传失败：', err);
      }
    });
  },

  // 跳转到我的照片页
  toPhotos() {
    wx.switchTab({
      url: '/pages/photos/photos'
    });
  }
});
```

#### 3. 我的照片页面（pages/photos/photos）

##### 3.1 WXML（photos.wxml）

```XML
<view class="container">
  <!-- 空状态 -->
  <view wx:if="{{!photoList.length}}" class="empty">
    <icon type="image" size="80" color="#ccc"></icon>
    <text>暂无照片，快去上传吧</text>
  </view>

  <!-- 照片列表 -->
  <view wx:else class="photo-list">
    <view class="photo-item" wx:for="{{photoList}}" wx:key="id">
      <!-- 处理后的照片 -->
      <image src="{{item.processedUrl}}" mode="aspectFill"></image>
      <!-- 过期提示 -->
      <view wx:if="{{item.isExpired}}" class="expired-tag">已过期</view>
      <!-- 操作按钮 -->
      <view class="photo-actions">
        <button 
          bindtap="downloadPhoto" 
          data-url="{{item.processedUrl}}"
          disabled="{{item.isExpired}}"
        >
          {{item.isExpired ? '已过期' : '下载'}}
        </button>
        <button bindtap="deletePhoto" data-id="{{item.id}}">删除</button>
      </view>
    </view>
  </view>
</view>
```

##### 3.2 WXSS（photos.wxss）

```CSS
.container {
  padding: 20rpx;
  min-height: 100vh;
  background-color: #f5f5f5;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
  color: #ccc;
  font-size: 32rpx;
}

.photo-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20rpx;
}

.photo-item {
  position: relative;
  border-radius: 8rpx;
  overflow: hidden;
  background-color: #fff;
}

.photo-item image {
  width: 100%;
  height: 200rpx;
}

.expired-tag {
  position: absolute;
  top: 10rpx;
  right: 10rpx;
  background-color: #ff4444;
  color: #fff;
  font-size: 24rpx;
  padding: 5rpx 10rpx;
  border-radius: 4rpx;
}

.photo-actions {
  display: flex;
  padding: 10rpx;
}

.photo-actions button {
  flex: 1;
  font-size: 24rpx;
  height: 60rpx;
  line-height: 60rpx;
}

.photo-actions button:first-child {
  background-color: #0088ff;
  color: #fff;
  margin-right: 10rpx;
}

.photo-actions button:last-child {
  background-color: #fff;
  color: #ff4444;
  border: 1rpx solid #ff4444;
}
```

##### 3.3 JS（photos.js）：加载/下载/删除照片

```JavaScript
Page({
  data: {
    photoList: []  // 照片列表：[{id, originalUrl, processedUrl, createTime, isExpired}]
  },

  onShow() {
    this.getPhotoList();
  },

  // 获取用户照片列表（调用后端接口）
  getPhotoList() {
    const openid = wx.getStorageSync('openid');
    wx.request({
      url: 'https://你的后端域名/api/photos/list',
      method: 'GET',
      data: { openid },
      success: (res) => {
        if (res.data.code === 200) {
          // 处理过期逻辑（后端也可提前判断）
          const photoList = res.data.data.map(item => {
            // 计算创建时间到现在是否超过90天
            const createTime = new Date(item.createTime).getTime();
            const now = Date.now();
            const isExpired = (now - createTime) > 90 * 24 * 60 * 60 * 1000;
            return { ...item, isExpired };
          });
          this.setData({ photoList });
        } else {
          wx.showToast({ title: res.data.msg, icon: 'none' });
        }
      },
      fail: (err) => {
        wx.showToast({ title: '获取照片失败', icon: 'none' });
        console.error(err);
      }
    });
  },

  // 下载照片到相册
  downloadPhoto(e) {
    const url = e.currentTarget.dataset.url;
    wx.showLoading({ title: '下载中...' });

    // 1. 先下载文件到本地
    wx.downloadFile({
      url: url,
      success: (res) => {
        if (res.statusCode === 200) {
          // 2. 保存到相册（需要用户授权）
          wx.saveImageToPhotosAlbum({
            filePath: res.tempFilePath,
            success: () => {
              wx.hideLoading();
              wx.showToast({ title: '下载成功' });
            },
            fail: (err) => {
              wx.hideLoading();
              // 若用户拒绝授权，引导开启
              if (err.errMsg.includes('auth deny')) {
                wx.openSetting({
                  success: (settingRes) => {
                    if (settingRes.authSetting['scope.writePhotosAlbum']) {
                      this.downloadPhoto(e);
                    } else {
                      wx.showToast({ title: '需授权保存相册才能下载', icon: 'none' });
                    }
                  }
                });
              } else {
                wx.showToast({ title: '保存失败', icon: 'none' });
              }
            }
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        wx.showToast({ title: '下载失败', icon: 'none' });
        console.error(err);
      }
    });
  },

  // 删除照片
  deletePhoto(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '提示',
      content: '确定删除这张照片吗？删除后不可恢复',
      success: (res) => {
        if (res.confirm) {
          wx.request({
            url: 'https://你的后端域名/api/photos/delete',
            method: 'POST',
            data: { id, openid: wx.getStorageSync('openid') },
            success: (res) => {
              if (res.data.code === 200) {
                wx.showToast({ title: '删除成功' });
                this.getPhotoList(); // 重新加载列表
              } else {
                wx.showToast({ title: res.data.msg, icon: 'none' });
              }
            }
          });
        }
      }
    });
  }
});
```

#### 4. 我的信息页面（pages/profile/profile）

##### 4.1 WXML（profile.wxml）

```XML
<view class="container">
  <!-- 账号信息 -->
  <view class="profile-card">
    <view class="avatar">
      <image src="{{userInfo.avatarUrl || '/images/avatar.png'}}"></image>
    </view>
    <view class="info">
      <text class="nickname">{{userInfo.nickName || '未登录'}}</text>
      <text class="openid">账号：{{openid || '未获取'}}</text>
    </view>
  </view>

  <!-- 剩余张数 -->
  <view class="count-card">
    <text class="label">剩余可处理照片</text>
    <text class="count">{{remainCount}} 张</text>
    <button bindtap="recharge">立即充值</button>
  </view>

  <!-- 充值选项 -->
  <view class="recharge-list" wx:if="{{showRecharge}}">
    <view class="recharge-item" wx:for="{{rechargeOptions}}" wx:key="id" bindtap="chooseRecharge" data-item="{{item}}">
      <text class="price">¥{{item.price}}</text>
      <text class="desc">{{item.count}} 张照片处理次数</text>
      <icon wx:if="{{selectedRechargeId === item.id}}" type="success" color="#0088ff"></icon>
    </view>
    <button class="pay-btn" bindtap="pay">确认支付</button>
  </view>
</view>
```

##### 4.2 WXSS（profile.wxss）

```CSS
.container {
  padding: 20rpx;
  min-height: 100vh;
  background-color: #f5f5f5;
}

.profile-card {
  display: flex;
  align-items: center;
  padding: 30rpx;
  background-color: #fff;
  border-radius: 10rpx;
  margin-bottom: 20rpx;
}

.avatar image {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
}

.info {
  margin-left: 30rpx;
}

.nickname {
  font-size: 36rpx;
  font-weight: bold;
  margin-bottom: 10rpx;
}

.openid {
  font-size: 24rpx;
  color: #999;
}

.count-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 30rpx;
  background-color: #fff;
  border-radius: 10rpx;
  margin-bottom: 20rpx;
}

.label {
  font-size: 32rpx;
  color: #666;
}

.count {
  font-size: 48rpx;
  font-weight: bold;
  color: #0088ff;
}

.count-card button {
  background-color: #0088ff;
  color: #fff;
  border-radius: 8rpx;
  padding: 0 30rpx;
}

.recharge-list {
  background-color: #fff;
  border-radius: 10rpx;
  padding: 20rpx;
}

.recharge-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.recharge-item:last-child {
  border-bottom: none;
}

.price {
  font-size: 36rpx;
  font-weight: bold;
  color: #ff4444;
}

.desc {
  font-size: 28rpx;
  color: #666;
}

.pay-btn {
  width: 100%;
  background-color: #ff4444;
  color: #fff;
  height: 80rpx;
  line-height: 80rpx;
  font-size: 32rpx;
  border-radius: 8rpx;
  margin-top: 20rpx;
}
```

##### 4.3 JS（profile.js）：用户信息/充值逻辑

```JavaScript
Page({
  data: {
    openid: '',
    userInfo: {},
    remainCount: 0,        // 剩余可处理张数
    showRecharge: false,   // 是否显示充值选项
    rechargeOptions: [     // 充值套餐
      { id: 1, price: 9.9, count: 10 },
      { id: 2, price: 19.9, count: 25 },
      { id: 3, price: 29.9, count: 50 }
    ],
    selectedRechargeId: 1  // 默认选中第一个套餐
  },

  onShow() {
    this.getUserInfo();
  },

  // 获取用户信息（openid、剩余张数等）
  getUserInfo() {
    const openid = wx.getStorageSync('openid');
    if (!openid) {
      // 未登录，先执行登录逻辑（获取openid）
      this.login();
      return;
    }

    this.setData({ openid });
    // 获取用户信息和剩余张数
    wx.request({
      url: 'https://你的后端域名/api/user/info',
      method: 'GET',
      data: { openid },
      success: (res) => {
        if (res.data.code === 200) {
          this.setData({
            userInfo: res.data.data.userInfo,
            remainCount: res.data.data.remainCount
          });
        }
      }
    });

    // 获取微信用户头像/昵称（需用户授权）
    wx.getUserProfile({
      desc: '用于展示账号信息',
      success: (res) => {
        this.setData({ userInfo: res.userInfo });
      }
    });
  },

  // 小程序登录：获取openid（后端需对接微信登录接口）
  login() {
    wx.login({
      success: (res) => {
        wx.request({
          url: 'https://你的后端域名/api/login',
          method: 'POST',
          data: { code: res.code },
          success: (loginRes) => {
            if (loginRes.data.code === 200) {
              wx.setStorageSync('openid', loginRes.data.data.openid);
              this.setData({ openid: loginRes.data.data.openid });
              this.getUserInfo();
            }
          }
        });
      }
    });
  },

  // 显示充值选项
  recharge() {
    this.setData({ showRecharge: true });
  },

  // 选择充值套餐
  chooseRecharge(e) {
    const item = e.currentTarget.dataset.item;
    this.setData({ selectedRechargeId: item.id });
  },

  // 支付（对接微信支付）
  pay() {
    const selectedItem = this.data.rechargeOptions.find(item => item.id === this.data.selectedRechargeId);
    const openid = this.data.openid;

    wx.request({
      url: 'https://你的后端域名/api/pay/createOrder',
      method: 'POST',
      data: {
        openid,
        price: selectedItem.price,
        count: selectedItem.count,
        orderType: 'photo_count'
      },
      success: (res) => {
        if (res.data.code === 200) {
          // 调用微信支付
          wx.requestPayment({
            timeStamp: res.data.data.timeStamp,
            nonceStr: res.data.data.nonceStr,
            package: res.data.data.package,
            signType: 'MD5',
            paySign: res.data.data.paySign,
            success: () => {
              wx.showToast({ title: '充值成功' });
              this.setData({ showRecharge: false });
              this.getUserInfo(); // 刷新剩余张数
            },
            fail: (err) => {
              wx.showToast({ title: '支付失败', icon: 'none' });
              console.error(err);
            }
          });
        }
      }
    });
  }
});
```

### 三、后端核心逻辑（简要说明）

前端依赖后端完成以下关键功能，这里以 Node.js + Express 为例给出核心接口示例：

```JavaScript
// 1. 登录接口：获取openid
app.post('/api/login', async (req, res) => {
  const { code } = req.body;
  // 调用微信接口换取openid（需小程序appid和secret）
  const response = await axios.get(`https://api.weixin.qq.com/sns/jscode2session?appid=你的appid&secret=你的secret&js_code=${code}&grant_type=authorization_code`);
  res.json({ code: 200, data: { openid: response.data.openid } });
});

// 2. 上传照片接口
app.post('/api/upload', async (req, res) => {
  const { openid } = req.body;
  const photoFile = req.files.photo; // 需用multer处理文件上传
  
  // 1. 保存原始照片到云存储（设置90天过期）
  const originalUrl = await uploadToOSS(photoFile.path, openid, 'original');
  
  // 2. 处理照片（调用图像处理逻辑，如抠图/滤镜等）
  const processedUrl = await processPhoto(photoFile.path, openid);
  
  // 3. 扣减用户剩余张数
  await updateUserCount(openid, -1);
  
  // 4. 保存照片记录到数据库
  await savePhotoRecord(openid, originalUrl, processedUrl);
  
  res.json({ code: 200, data: { id: photoId } });
});

// 3. 充值创建订单接口（对接微信支付）
app.post('/api/pay/createOrder', async (req, res) => {
  const { openid, price, count } = req.body;
  // 生成微信支付订单（需商户号、API密钥等）
  const order = await createWxPayOrder(openid, price, count);
  res.json({ code: 200, data: order });
});
```

### 四、关键注意事项

1. **小程序配置**：
   1. 需在微信公众平台配置“服务器域名”（uploadFile、downloadFile、request 域名）；
   2. 照片处理功能若涉及敏感内容，需完成小程序类目审核。
2. **存储策略**：
   1. 云存储需配置文件过期规则（90天自动删除），避免存储冗余；
   2. 敏感照片建议加密存储，仅用户本人可访问。
3. **支付对接**：
   1. 充值功能需要小程序完成企业认证，且对接微信支付商户号；
   2. 支付回调需校验签名，确保订单有效性。
4. **照片处理**：
   1. 后端可使用 Node.js 的 sharp 库处理图片，或调用第三方 AI 抠图/美化接口；
   2. 处理耗时较长时，建议用异步队列，处理完成后推送通知给用户。

### 总结

1. 小程序核心架构：前端通过 tabBar 实现三个功能入口，后端负责照片存储/处理、用户信息/充值管理；
2. 核心功能实现：
   1. 上传照片：wx.chooseImage + wx.uploadFile 完成本地选择和上传；
   2. 我的照片：加载用户照片列表，wx.downloadFile + wx.saveImageToPhotosAlbum 实现下载；
   3. 我的信息：基于 openid 标识用户，对接微信支付实现充值；
3. 关键细节：照片存储设置90天过期、下载需用户授权、充值对接微信支付需企业认证。

你可基于上述代码框架，补充后端具体实现、完善UI样式、对接实际的照片处理逻辑，即可完成小程序的核心功能开发。