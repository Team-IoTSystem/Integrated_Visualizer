//id=1を返す例
(async () => {
    await fetch(URL(), {
        method: 'GET',
    })
        .then((response) => response.text())
        .then((text) => console.log(text))
        .catch((error) => console.log(error));
})();

//id=20を返す例
(async () => {
    await fetch('http://localhost:3000/Packet/:id?id=20', {
        method: 'GET',
    })
        .then((response) => response.text())
        .then((text) => console.log(text))
        .catch((error) => console.log(error));
})();

//idが一番古い（つまり新しい情報をとる）
(async () => {
    await fetch('http://localhost:3000/Packet/new', {
        method: 'GET',
    })
        .then((response) => response.text())
        .then((text) => console.log(text))
        .catch((error) => console.log(error));
})();