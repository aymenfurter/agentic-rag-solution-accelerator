import { InteractiveBrowserCredential } from "@azure/identity";

export const getAuthToken = async () => {
  const credential = new InteractiveBrowserCredential();
  const token = await credential.getToken("https://cognitiveservices.azure.com/.default");
  return token.token;
};

export const isAuthenticated = () => {
  // For development, return true
  // TODO: Implement proper authentication check
  return true;
};

export const login = async () => {
  // TODO: Implement login logic
  return true;
};

export const logout = async () => {
  // TODO: Implement logout logic
  return true;
};