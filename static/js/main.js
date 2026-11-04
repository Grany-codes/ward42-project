document.addEventListener('DOMContentLoaded', function() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js').catch(err => console.log('SW failed', err));
    }

    const reportForm = document.getElementById('reportForm');
    if (reportForm) {
        reportForm.addEventListener('submit', function(e) {
            const desc = document.getElementById('description').value;
            const cell = document.getElementById('reporter_cell').value;
            let valid = true;
            
            document.getElementById('descError').innerText = '';
            document.getElementById('cellError').innerText = '';

            if (desc.length < 10 || desc.length > 500) {
                document.getElementById('descError').innerText = 'Description must be 10 to 500 characters.';
                valid = false;
            }
            if (!/^0\d{9}$/.test(cell)) {
                document.getElementById('cellError').innerText = 'Enter a valid 10-digit SA cell number starting with 0.';
                valid = false;
            }
            if (!valid) {
                e.preventDefault();
            } else {
                localStorage.removeItem('draft_category');
                localStorage.removeItem('draft_street');
                localStorage.removeItem('draft_description');
            }
        });
    }

    const filterCategory = document.getElementById('filterCategory');
    const filterStatus = document.getElementById('filterStatus');
    if (filterCategory && filterStatus) {
        const applyFilter = () => {
            const rows = document.querySelectorAll('.report-row');
            rows.forEach(row => {
                const matchCat = !filterCategory.value || row.dataset.category === filterCategory.value;
                const matchStat = !filterStatus.value || row.dataset.status === filterStatus.value;
                row.style.display = (matchCat && matchStat) ? '' : 'none';
            });
        };
        filterCategory.addEventListener('change', applyFilter);
        filterStatus.addEventListener('change', applyFilter);
    }

    const fields = ['category', 'street', 'description'];
    fields.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.value = localStorage.getItem('draft_' + id) || '';
            el.addEventListener('input', () => {
                try {
                    localStorage.setItem('draft_' + id, el.value);
                } catch (e) {
                    console.error('Local storage error', e);
                }
            });
        }
    });

    const categoryList = document.getElementById('categoryList');
    if (categoryList) {
        fetch('/api/reports/summary')
            .then(response => response.json())
            .then(data => {
                for (const [cat, count] of Object.entries(data.categories)) {
                    categoryList.innerHTML += `<li class="list-group-item d-flex justify-content-between">${cat} <span class="badge bg-primary rounded-pill">${count}</span></li>`;
                }
                const statusList = document.getElementById('statusList');
                for (const [stat, count] of Object.entries(data.statuses)) {
                    statusList.innerHTML += `<li class="list-group-item d-flex justify-content-between">${stat} <span class="badge bg-success rounded-pill">${count}</span></li>`;
                }
            })
            .catch(err => console.error('Fetch error', err));
    }
});