document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generate-graph-btn');
    const entityIdInput = document.getElementById('entity-id-input');
    const statusDiv = document.getElementById('status');
    const container = document.getElementById('mynetwork');
    let network = null;

    generateBtn.addEventListener('click', async () => {
        const entityId = entityIdInput.value.trim();
        if (!entityId) {
            statusDiv.innerText = 'Пожалуйста, введите ID сущности.';
            return;
        }

        statusDiv.innerText = `Загрузка данных для ID: ${entityId}...`;
        if (network) {
            network.destroy();
            network = null;
        }

        try {
            const response = await fetch(`/api/graph?id=${entityId}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `Ошибка сети: ${response.statusText}`);
            }

            if (data.error) {
                throw new Error(data.error);
            }

            if (!data.nodes || data.nodes.length === 0) {
                statusDiv.innerText = `Данные для ID '${entityId}' не найдены.`;
                return;
            }

            statusDiv.innerText = 'Данные загружены. Построение графа...';

            const nodes = new vis.DataSet(data.nodes);
            const edges = new vis.DataSet(data.edges);
            const graphData = { nodes, edges };
            const options = {
                physics: { enabled: true },
                edges: { 
                    arrows: { to: { enabled: true, scaleFactor: 0.5 } },
                    font: { align: 'top' }
                },
                interaction: { hover: true }
            };
            network = new vis.Network(container, graphData, options);

            network.on("click", function (params) {
                if (params.edges.length > 0) {
                    const edgeId = params.edges[0];
                    const edge = edges.get(edgeId);
                    if (edge && edge.time) {
                        // Check if the label is currently showing the time.
                        if (edge.label && edge.label.startsWith('Время:')) {
                            // If it is, revert to the original relation name from the 'title' property.
                            edges.update({ 
                                id: edgeId, 
                                label: edge.title, 
                                font: { multi: false, background: 'none' } // Revert font style
                            });
                        } else {
                            // If it's not showing the time, show it.
                            const newLabel = `Время:\n${edge.time}`;
                            edges.update({ 
                                id: edgeId, 
                                label: newLabel, 
                                font: { multi: true, background: 'rgba(255,255,255,0.85)' } // Apply special font style
                            });
                        }
                    }
                }
            });

            statusDiv.innerText = 'Готово.';

        } catch (error) {
            statusDiv.innerText = `Критическая ошибка: ${error.message}`;
            console.error("Ошибка:", error);
        }
    });

    statusDiv.innerText = 'Введите ID сущности и нажмите "Построить граф".';
});
