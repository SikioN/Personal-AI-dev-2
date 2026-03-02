async function main() {
    const statusDiv = document.getElementById('status');
    statusDiv.innerText = 'Загрузка данных графа...';

    try {
        const [nodesResponse, edgesResponse] = await Promise.all([
            fetch('nodes.json'),
            fetch('edges.json')
        ]);

        if (!nodesResponse.ok || !edgesResponse.ok) {
            throw new Error(`Ошибка сети: ${nodesResponse.statusText} / ${edgesResponse.statusText}`);
        }

        const nodes_data = await nodesResponse.json();
        const edges_data = await edgesResponse.json();

        if (nodes_data.length === 0) {
            statusDiv.innerText = 'Данные для отображения не найдены. Запустите: python generate_data.py <ID>';
            return;
        }

        statusDiv.innerText = 'Данные загружены. Построение графа...';

        const container = document.getElementById('mynetwork');
        const nodes = new vis.DataSet(nodes_data);
        const edges = new vis.DataSet(edges_data);
        const data = { nodes: nodes, edges: edges };
        const options = {
            physics: { enabled: true },
            edges: { 
                arrows: { to: { enabled: true, scaleFactor: 0.5 } },
                font: { align: 'top' }
            },
            interaction: { hover: true }
        };
        const network = new vis.Network(container, data, options);
        
        let lastClickedEdge = null;

        // --- ИСПРАВЛЕНО: Улучшенный обработчик клика ---
        network.on("click", function (params) {
            // Сначала сбрасываем предыдущее выделенное ребро
            if (lastClickedEdge) {
                try {
                    const oldEdge = edges.get(lastClickedEdge.id);
                    if (oldEdge) {
                        edges.update({
                            id: lastClickedEdge.id,
                            label: lastClickedEdge.originalLabel,
                            font: { multi: false, background: 'rgba(255,255,255,0)' }
                        });
                    }
                } catch(e) { /* если ребро уже удалено */ }
                lastClickedEdge = null;
            }

            // Если клик был по новому ребру, обновляем его
            if (params.edges.length > 0) {
                const edgeId = params.edges[0];
                const edge = edges.get(edgeId);
                if (edge) {
                    // Сохраняем оригинальную метку для отката
                    lastClickedEdge = { id: edgeId, originalLabel: edge.label };

                    const newLabel = `Время:\n${edge.time || 'не указано'}`;

                    // Обновляем ребро, чтобы показать новую многострочную метку
                    edges.update({
                        id: edgeId,
                        label: newLabel,
                        font: { multi: true, background: 'rgba(255,255,255,0.85)', align: 'top' }
                    });
                }
            }
        });

        statusDiv.innerText = 'Готово.';

    } catch (error) {
        statusDiv.innerText = 'Критическая ошибка при загрузке или отрисовке графа.';
        console.error("Ошибка:", error);
    }
}

document.addEventListener('DOMContentLoaded', main);
