const initDashboardCharts = (pipelineData) => {
    const ctx = document.getElementById('pipelineChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Leads', 'Opportunities', 'Quotations', 'Orders'],
            datasets: [{
                label: 'Volume',
                data: [
                    pipelineData.leads,
                    pipelineData.opportunities,
                    pipelineData.quotations,
                    pipelineData.orders
                ],
                backgroundColor: '#2563EB',
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, grid: { display: false } },
                x: { grid: { display: false } }
            }
        }
    });
};
