document.getElementById('form-type').addEventListener('change', function () {
    let questionsCard = document.querySelector('.questions-list').closest('.card');
    let pushNotificationContainer = document.getElementById('push-notification-container');
    let notificationRecipients = document.getElementById('notification-recipients');
    
    if (this.value === 'NOTIFICATION') {
        questionsCard.style.display = 'none';
        pushNotificationContainer.style.display = 'block'; // Show the button
        notificationRecipients.style.display = 'block'; // Show the recipients select
    } else {
        questionsCard.style.display = 'block';
        pushNotificationContainer.style.display = 'none'; // Hide the button
        notificationRecipients.style.display = 'none'; // Hide the recipients select
    }
});

// Trigger the change event on page load to apply the logic initially
document.getElementById('form-type').dispatchEvent(new Event('change'));


// Optional function to handle the push notification button click
function enablePushNotification() {
    alert('Push notifications via email enabled!');
}
