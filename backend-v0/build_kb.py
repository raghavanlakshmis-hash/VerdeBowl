from rag import build_menu_collection, search_menu

if __name__ == "__main__":
    build_menu_collection()
    print("Collection built. Smoke test:")
    for doc in search_menu("what's in the barbacoa bowl"):
        print(" -", doc)
