import os


def load_templates_as_env_vars(template_dir: str = "templates") -> None:
    """Load all template files in the specified directory as environment variables."""
    for fn in os.listdir(template_dir):
        fpath = os.path.join(template_dir, fn)
        with open(fpath, encoding="utf-8") as f:
            template = f.read()
        env_var_name = os.path.splitext(fn)[0].upper() + "_TEMPLATE"
        os.environ[env_var_name] = template
