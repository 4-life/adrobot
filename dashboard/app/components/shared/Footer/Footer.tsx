export function Footer() {
  return (
    <footer className="border-t">
      <div className="mx-auto max-w-6xl p-4 text-xs text-muted-foreground">
        AdRobot · {new Date().getFullYear()}
      </div>
    </footer>
  );
}
