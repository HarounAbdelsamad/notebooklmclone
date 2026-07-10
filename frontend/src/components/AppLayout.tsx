import { UserButton } from "@clerk/clerk-react";
import { Link, Outlet } from "react-router-dom";

export function AppLayout() {
  return (
    <>
      <header className="app-header">
        <h1>
          <Link to="/">📓 NotebookLM Clone</Link>
        </h1>
        <UserButton afterSignOutUrl="/sign-in" />
      </header>
      <Outlet />
    </>
  );
}
