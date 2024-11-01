const userId = localStorage.getItem('userId');

if (userId) {
    fetch(`/get_receipts?userId=${userId}`)
        .then(response => response.json())
        .then(data => {
            // Handle the data, e.g., display the receipt links
            console.log(data.receipt_links);
            // Code to dynamically display receipts can go here
        })
        .catch(error => {
            console.error('Error fetching receipts:', error);
        });
} else {
    console.error('User ID is not available in localStorage.');
}
