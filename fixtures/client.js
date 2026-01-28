import axios from 'axios';

function doLogin() {
    axios.post('/users/login', { username: 'test' });
}

function fetchProduct(id) {
    // 模拟模版字符串
    const url = `/products/${id}`;
    axios.get(url);
}

// TODO: remove /old/legacy-endpoint