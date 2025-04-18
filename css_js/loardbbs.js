function loadBbs() {
    fetch('./bbs.py')
        .then(response => {
            if (!response.ok) throw new Error('BBS読み込み失敗');
            return response.text();
        })
        .then(data => {
            const bbsDiv = document.getElementById('bbs');
            bbsDiv.innerHTML = data;
            const form = bbsDiv.querySelector('form');
            if (form) {
                form.addEventListener('submit', (event) => {
                    event.preventDefault();
                    const formData = new FormData(form);
                    formData.append('ajax', 'true');
                    fetch(form.action, {
                        method: 'POST',
                        body: formData
                    })
                        .then(response => {
                            if (!response.ok) throw new Error('投稿失敗');
                            return response.json();
                        })
                        .then(data => {
                            if (data.error) {
                                alert(data.error);
                            } else {
                                bbsDiv.querySelector('#log-area').innerHTML = data.log;
                                form.querySelector('input[name="csrf_token"]').value = data.csrf_token;
                                form.querySelector('input[name="bbs_txt"]').value = '';
                            }
                        })
                        .catch(error => {
                            console.error('投稿エラー:', error);
                            bbsDiv.innerHTML = '<p>投稿に失敗しました</p>';
                        });
                });
            }
        })
        .catch(error => {
            console.error('BBS読み込みエラー:', error);
            bbsDiv.innerHTML = '<p>掲示板の読み込みに失敗しました</p>';
        });
}

loadBbs();
