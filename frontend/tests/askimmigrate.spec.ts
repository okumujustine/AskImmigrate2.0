import { expect, test } from '@playwright/test';

test('AskImmigrate - page has correct title', async ({ page }) => {
  await page.goto('http://localhost:4044/');

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/AskImmigrate/);
});

test('AskImmigrate - displays welcome screen with example questions', async ({ page }) => {
  await page.goto('http://localhost:4044/');

  // Check for the main welcome heading
  await expect(page.getByRole('heading', { name: 'Welcome to AskImmigrate' })).toBeVisible();
  
  // Check for the description
  await expect(page.getByText('Ask any question about immigration and get detailed answers.')).toBeVisible();
  
  // Check for example questions section
  await expect(page.getByRole('heading', { name: 'Example questions:' })).toBeVisible();
  
  // Check for specific example questions
  await expect(page.getByText('"What is an F1 visa?"')).toBeVisible();
  await expect(page.getByText('"How to apply for a Green Card?"')).toBeVisible();
  await expect(page.getByText('"What documents do I need for H1B?"')).toBeVisible();
});

test('AskImmigrate - chat input form is functional', async ({ page }) => {
  await page.goto('http://localhost:4044/');

  // Check for the chat input form
  const chatInput = page.locator('form.chat-input-form');
  await expect(chatInput).toBeVisible();
  
  // Check for the textarea field (not input)
  const inputField = chatInput.locator('textarea.message-input');
  await expect(inputField).toBeVisible();
  await expect(inputField).toHaveAttribute('placeholder', /ask.*question/i);
  
  // Check for the send button
  const sendButton = chatInput.locator('button[type="submit"]');
  await expect(sendButton).toBeVisible();
});

test('AskImmigrate - loading animation appears when sending message', async ({ page }) => {
  // This test requires the backend to be running on port 8000
  await page.goto('http://localhost:4044/');

  // Find the textarea field and send button
  const inputField = page.locator('textarea.message-input');
  const sendButton = page.locator('button[type="submit"]');
  
  // Type a test question
  await inputField.fill('What is an F1 visa?');
  
  // Click send button
  await sendButton.click();
  
  // Check that loading message appears
  await expect(page.getByText(/analyzing.*question/i)).toBeVisible({ timeout: 2000 });
  
  // Check for the elegant loader dots
  await expect(page.locator('.loader-dots')).toBeVisible();
  
  // Check for the brain or search icon
  await expect(page.locator('.brain-icon, .search-icon')).toBeVisible();
});