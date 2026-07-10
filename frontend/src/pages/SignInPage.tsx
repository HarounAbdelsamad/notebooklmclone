import { SignIn } from "@clerk/clerk-react";

export function SignInPage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
      }}
    >
      <div style={{ textAlign: "center" }}>
        <h1 style={{ marginBottom: 24 }}>📓 NotebookLM Clone</h1>
        <SignIn routing="path" path="/sign-in" signUpUrl="/sign-in" />
      </div>
    </div>
  );
}
