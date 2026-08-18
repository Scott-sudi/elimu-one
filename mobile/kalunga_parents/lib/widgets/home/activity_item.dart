import 'package:flutter/material.dart';

import '../../constants/app_constants.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme_colors.dart';
import '../../models/home_models.dart';

/// Carte d'une activite recente.
class ActivityItem extends StatelessWidget {
  const ActivityItem({
    super.key,
    required this.activity,
    this.onTap,
  });

  final RecentActivity activity;
  final VoidCallback? onTap;

  Color get _iconBackground {
    switch (activity.type) {
      case ActivityType.bulletin:
        return AppColors.activityBulletin;
      case ActivityType.meeting:
        return AppColors.activityMeeting;
      case ActivityType.fees:
        return AppColors.activityFees;
      case ActivityType.info:
        return AppColors.primaryLight;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: context.appCard,
      borderRadius: BorderRadius.circular(AppConstants.radiusLarge),
      elevation: context.isDarkTheme ? 0 : 1,
      shadowColor: AppColors.shadow,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppConstants.radiusLarge),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: _iconBackground,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(activity.icon, color: Colors.white, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      activity.title,
                      style: TextStyle(
                        color: context.appTextPrimary,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      activity.subtitle,
                      style: TextStyle(
                        color: context.appTextSecondary,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      activity.timestampLabel,
                      style: TextStyle(
                        color: context.appTextSecondary.withOpacity(0.85),
                        fontSize: 11.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
