function toggleImageUpload() {
  const imageUploadSection = document.getElementById('image-upload-section');
  const addImageCheckbox = document.getElementById('add-image');
  
  // Toggle visibility of the image upload section based on the checkbox state
  if (addImageCheckbox.checked) {
    imageUploadSection.style.display = 'block';
  } else {
    imageUploadSection.style.display = 'none';
  }
}