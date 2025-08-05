import { expect, test } from '@playwright/test';

test('has AskImmigrate title', async ({ page }) => {
  await page.goto('http://localhost:4044/');
  await expect(page).toHaveTitle(/AskImmigrate/);
});

test('displays welcome message and example questions', async ({ page }) => {
  await page.goto('http://localhost:4044/');

  await expect(page.getByRole('heading', { name: 'Welcome to AskImmigrate' })).toBeVisible();
  
  await expect(page.getByText('Ask any question about immigration and get detailed answers.')).toBeVisible();
  
  await expect(page.getByRole('heading', { name: 'Example questions:' })).toBeVisible();
  
  // Check for specific example questions
  await expect(page.getByText('"What is an F1 visa?"')).toBeVisible();
  await expect(page.getByText('"How to apply for a Green Card?"')).toBeVisible();
  await expect(page.getByText('"What documents do I need for H1B?"')).toBeVisible();
});

test('has chat input form', async ({ page }) => {
  await page.goto('http://localhost:4044/');

  const chatInput = page.locator('form.chat-input-form');
  await expect(chatInput).toBeVisible();
  
  const inputField = chatInput.locator('textarea.message-input');
  await expect(inputField).toBeVisible();
  await expect(inputField).toHaveAttribute('placeholder', /ask.*question/i);
  
  // Check for the send button
  const sendButton = chatInput.locator('button[type="submit"]');
  await expect(sendButton).toBeVisible();
});

test('shows loading animation when sending a message', async ({ page }) => {
 
  await page.goto('http://localhost:4044/');

  
  const inputField = page.locator('textarea.message-input');
  const sendButton = page.locator('button[type="submit"]');
  

  await inputField.fill('What is an F1 visa?');
  
  await sendButton.click();
  
  await expect(page.getByText(/analyzing.*question/i)).toBeVisible({ timeout: 2000 });
  
  await expect(page.locator('.loader-dots')).toBeVisible();
  
  await expect(page.locator('.brain-icon, .search-icon')).toBeVisible();
});