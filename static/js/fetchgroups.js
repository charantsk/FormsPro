    document.addEventListener('DOMContentLoaded', async () => {
        try {
            const response = await fetch('/api/enums');
            const enums = await response.json();
            
            // Populate class group select
            const classGroupSelect = document.getElementById('target-class-group');
            classGroupSelect.innerHTML = '<option value="">Select a Class Group</option>';
            
            enums.class_groups.forEach(group => {
                const option = document.createElement('option');
                option.value = group;
                option.textContent = group.replace(/_/g, ' ').toUpperCase();
                classGroupSelect.appendChild(option);
            });
    
        } catch (error) {
            console.error('Error fetching enums:', error);
        }
    });