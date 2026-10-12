#if DEBUG
import Foundation
import Combine

/// Preview-only alias so existing previews using `PurchasesModel()` resolve to the real StoreKit model.
/// This avoids renaming across the project while keeping release builds unaffected.
typealias PurchasesModel = PurchaseStore
#endif
