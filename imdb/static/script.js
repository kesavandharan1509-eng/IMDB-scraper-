document.addEventListener('DOMContentLoaded', () => {
    const scrapeBtn = document.getElementById('scrapeBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const loader = document.getElementById('loader');
    const resultMessage = document.getElementById('resultMessage');
    const dataDashboard = document.getElementById('dataDashboard');
    const tableBody = document.getElementById('tableBody');
    const ratingFilter = document.getElementById('ratingFilter');
    const totalMoviesEl = document.getElementById('totalMovies');
    const avgRatingEl = document.getElementById('avgRating');

    let currentMovieData = [];

    // Load existing data on page load
    fetchInitialData();

    async function fetchInitialData() {
        try {
            const response = await fetch('/api/data');
            const result = await response.json();
            if (result.success && result.data.length > 0) {
                currentMovieData = result.data;
                // DO NOT SHOW DOWNLOAD BUTTON INITIALLY 
                // ONLY AFTER EXPLICIT SCRAPE
                updateDashboard();
            }
        } catch (error) {
            console.error("No initial data found or error loading it.");
        }
    }

    scrapeBtn.addEventListener('click', async () => {
        // UI Reset
        scrapeBtn.disabled = true;
        scrapeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scraping...';
        loader.classList.remove('hidden');
        resultMessage.classList.add('hidden');
        dataDashboard.classList.add('hidden');
        downloadBtn.classList.add('hidden');

        try {
            const response = await fetch('/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            loader.classList.add('hidden');
            resultMessage.classList.remove('hidden');

            if (result.success) {
                resultMessage.textContent = result.message;
                resultMessage.className = 'message success';
                
                // Show download button ONLY AFTER SCRAPE IS DONE
                downloadBtn.classList.remove('hidden');
                
                if (result.data && result.data.length > 0) {
                    currentMovieData = result.data;
                    updateDashboard();
                }
            } else {
                resultMessage.textContent = "Error: " + result.message;
                resultMessage.className = 'message error';
            }
        } catch (error) {
            loader.classList.add('hidden');
            resultMessage.textContent = "Request failed: " + error.message;
            resultMessage.className = 'message error';
            resultMessage.classList.remove('hidden');
        } finally {
            scrapeBtn.disabled = false;
            scrapeBtn.innerHTML = '<i class="fa-solid fa-spider"></i> Scrape Fresh Data';
        }
    });

    ratingFilter.addEventListener('change', () => {
        updateDashboard();
    });

    function updateDashboard() {
        const minRating = parseFloat(ratingFilter.value);
        
        // Filter Data
        const filteredData = currentMovieData.filter(movie => {
            const r = parseFloat(movie.Rating || 0);
            return r >= minRating;
        });

        // Calculate Stats
        totalMoviesEl.textContent = filteredData.length;
        
        if (filteredData.length > 0) {
            const sum = filteredData.reduce((acc, curr) => acc + parseFloat(curr.Rating || 0), 0);
            const avg = (sum / filteredData.length).toFixed(2);
            avgRatingEl.textContent = avg;
        } else {
            avgRatingEl.textContent = "0.0";
        }

        // Populate Table
        tableBody.innerHTML = '';
        filteredData.forEach(movie => {
            // Main Row
            const tr = document.createElement('tr');
            tr.className = 'movie-row';
            
            const tdRank = document.createElement('td');
            tdRank.textContent = movie.Rank;
            
            const tdTitle = document.createElement('td');
            tdTitle.style.fontWeight = 'bold';
            tdTitle.textContent = movie.Title;
            
            const tdDetailsBtn = document.createElement('td');
            tdDetailsBtn.innerHTML = '<button class="expand-btn"><i class="fa-solid fa-chevron-down"></i></button>';
            
            tr.appendChild(tdRank);
            tr.appendChild(tdTitle);
            tr.appendChild(tdDetailsBtn);
            
            // Details Row
            const detailsTr = document.createElement('tr');
            detailsTr.className = 'details-row hidden';
            const detailsTd = document.createElement('td');
            detailsTd.colSpan = 3;
            
            detailsTd.innerHTML = `
                <div class="movie-details">
                    <div class="detail-item" title="Release Year"><i class="fa-regular fa-calendar"></i> <strong>Year:</strong> ${movie.Year}</div>
                    <div class="detail-item" title="IMDb Rating"><i class="fa-solid fa-star"></i> <strong>Rating:</strong> ${movie.Rating}</div>
                    <div class="detail-item" title="Total Votes"><i class="fa-solid fa-users"></i> <strong>Votes:</strong> ${movie.Votes || 'N/A'}</div>
                    <div class="detail-item" title="Duration"><i class="fa-regular fa-clock"></i> <strong>Duration:</strong> ${movie.Duration || 'N/A'}</div>
                </div>
            `;
            detailsTr.appendChild(detailsTd);

            // Toggle logic
            tr.addEventListener('click', () => {
                const isHidden = detailsTr.classList.contains('hidden');
                
                // Optional: Close all other open rows
                document.querySelectorAll('.details-row').forEach(row => row.classList.add('hidden'));
                document.querySelectorAll('.expand-btn i').forEach(icon => icon.className = 'fa-solid fa-chevron-down');
                document.querySelectorAll('.movie-row').forEach(row => row.classList.remove('active-row'));
                
                if (isHidden) {
                    detailsTr.classList.remove('hidden');
                    tdDetailsBtn.querySelector('i').className = 'fa-solid fa-chevron-up';
                    tr.classList.add('active-row');
                }
            });
            
            tableBody.appendChild(tr);
            tableBody.appendChild(detailsTr);
        });

        dataDashboard.classList.remove('hidden');
    }
});
