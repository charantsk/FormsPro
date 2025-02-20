        // Function to fetch forms from the API
        async function fetchForms() {
    try {
        const response = await fetch('/api/forms');
        if (!response.ok) {
            throw new Error('Failed to fetch forms');
        }
        const data = await response.json();
        renderForms(data);
    } catch (error) {
        console.error('Error fetching forms:', error);
        // You might want to show an error message to the user
    }
}
        // Function to render the forms in the table
        function renderForms(data) {
            const tableBody = document.querySelector("#forms-table tbody");
            tableBody.innerHTML = ''; // Clear existing rows
        
            const allForms = [...(data.forms || []), ...(data.notifications || [])];
        
            if (allForms.length === 0) {
                const emptyRow = document.createElement('tr');
                emptyRow.innerHTML = `
                    <td colspan="4" class="text-center py-4">
                        No forms found. Create a new form to get started.
                    </td>
                `;
                tableBody.appendChild(emptyRow);
                return;
            }
        
            allForms.forEach(form => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${form.title}</td>
                    <td>${form.description || ''}</td>
                    <td class="action-buttons">
                        <a href="/admin/view_form?form_id=${form.id}" class="btn view-btn">View/Edit</a>
                        <button class="btn delete-btn" data-id="${form.id}" title="Delete">
                            <i class="fas fa-trash-alt"></i> Delete
                        </button>
                    </td>
                `;
        
                tableBody.appendChild(row);
            });
        
            // Attach event listeners to all delete buttons
            document.querySelectorAll('.delete-btn').forEach(button => {
                button.addEventListener('click', async (event) => {
                    const formId = event.target.closest('.delete-btn').dataset.id;
                    await deleteForm(formId, event.target.closest('tr'));
                });
            });
        }
        
        

        async function deleteForm(formId, rowElement) {
            if (!confirm("Are you sure you want to delete this form?")) return;
        
            try {
                const response = await fetch(`/api/forms/${formId}`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' }
                });
        
                if (!response.ok) {
                    throw new Error('Failed to delete form');
                }
        
                // Remove row from UI
                rowElement.remove();
            } catch (error) {
                console.error('Error deleting form:', error);
                alert('Failed to delete form.');
            }
        }
        

        // Initial fetch when the page loads
        // Initial fetch when the page loads
document.addEventListener('DOMContentLoaded', () => {
    fetchForms();
});
        // Remove the modal-related code since we're now navigating to a new page
        // Remove openModal and closeModal functions